import pyotp
from datetime import datetime, timedelta, timezone

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

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/login", response_model=Token)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None

    # First check if user exists and is locked (before password check)
    user_check = db.query(User).filter(User.username == data.username).first()
    if user_check and user_check.locked_until:
        if datetime.now(timezone.utc) < user_check.locked_until:
            remaining = int(
                (user_check.locked_until - datetime.now(timezone.utc)).total_seconds() / 60
            )
            log_action(
                db,
                user_id=user_check.id,
                action="login_blocked",
                resource="auth",
                detail=f"Cuenta bloqueada, {remaining + 1} min restantes",
                ip_address=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Cuenta bloqueada por demasiados intentos fallidos. "
                f"Intente en {remaining + 1} minutos o contacte al administrador.",
            )
        else:
            # Lock expired, reset
            user_check.locked_until = None
            user_check.failed_login_attempts = 0
            db.commit()

    user = authenticate_user(db, data.username, data.password)
    if not user:
        # Increment failed attempts
        if user_check and user_check.is_active:
            user_check.failed_login_attempts = (
                user_check.failed_login_attempts or 0
            ) + 1
            if user_check.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user_check.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCKOUT_MINUTES
                )
                log_action(
                    db,
                    user_id=user_check.id,
                    action="account_locked",
                    resource="auth",
                    detail=f"Cuenta bloqueada tras {MAX_FAILED_ATTEMPTS} intentos fallidos",
                    ip_address=client_ip,
                )
            db.commit()

        log_action(
            db,
            user_id=user_check.id if user_check else None,
            action="login_failed",
            resource="auth",
            detail=f"Intento fallido para usuario: {data.username[:50]}",
            ip_address=client_ip,
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
                ip_address=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código de verificación incorrecto",
            )

    # Successful login - reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None

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
        ip_address=client_ip,
    )

    db.commit()
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
