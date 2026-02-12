import pyotp
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import (
    UserLogin,
    Token,
    UserResponse,
    TOTPSetupResponse,
    TOTPVerify,
    PasswordChange,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    verify_password,
    hash_password,
)
from app.services.audit import log_action
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.username, data.password)
    if not user:
        log_action(
            db,
            user_id=None,
            action="login_failed",
            resource="auth",
            detail=f"Intento fallido para usuario: {data.username[:50]}",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    # If user has TOTP enabled, verify the code
    if user.totp_enabled:
        if not data.totp_code:
            return Token(access_token="", totp_required=True)

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(data.totp_code, valid_window=1):
            log_action(
                db,
                user_id=user.id,
                action="totp_failed",
                resource="auth",
                detail="Código TOTP incorrecto",
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código de verificación incorrecto",
            )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "department": user.department.value,
        }
    )

    log_action(
        db,
        user_id=user.id,
        action="login",
        resource="auth",
        detail="Inicio de sesión exitoso",
        ip_address=request.client.host if request.client else None,
    )

    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ─── TOTP 2FA Endpoints ────────────────────────────────────────


@router.post("/totp/setup", response_model=TOTPSetupResponse)
def totp_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a TOTP secret and provisioning URI for Google Authenticator."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA ya está habilitado en esta cuenta",
        )

    secret = pyotp.random_base32()
    # Save the secret (not yet enabled until verified)
    current_user.totp_secret = secret
    db.commit()

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="SantoniBot",
    )

    log_action(
        db,
        user_id=current_user.id,
        action="totp_setup",
        resource="auth",
        detail="Configuración 2FA iniciada",
    )

    return TOTPSetupResponse(secret=secret, qr_uri=uri)


@router.post("/totp/enable")
def totp_enable(
    data: TOTPVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify a TOTP code and enable 2FA for the user."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA ya está habilitado",
        )
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debe configurar 2FA con /auth/totp/setup",
        )

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.totp_code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código incorrecto. Intente de nuevo.",
        )

    current_user.totp_enabled = True
    db.commit()

    log_action(
        db,
        user_id=current_user.id,
        action="totp_enabled",
        resource="auth",
        detail="2FA habilitado exitosamente",
    )

    return {"message": "2FA habilitado exitosamente"}


@router.post("/totp/disable")
def totp_disable(
    data: TOTPVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable 2FA (requires current TOTP code to confirm)."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA no está habilitado",
        )

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.totp_code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código incorrecto",
        )

    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()

    log_action(
        db,
        user_id=current_user.id,
        action="totp_disabled",
        resource="auth",
        detail="2FA deshabilitado",
    )

    return {"message": "2FA deshabilitado"}


# ─── Password Change ───────────────────────────────────────────


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password (enforces password policy)."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta",
        )

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()

    log_action(
        db,
        user_id=current_user.id,
        action="password_changed",
        resource="auth",
        detail="Contraseña actualizada",
    )

    return {"message": "Contraseña actualizada exitosamente"}
