import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db, IdempiereSession
from app.middleware.auth import require_admin
from app.models.user import User, UserRole, Department
from app.models.conversation import Conversation
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.auth import hash_password, verify_password

logger = logging.getLogger("santonibot.users")

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/", response_model=list[UserResponse])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    conv_count = (
        db.query(Conversation.user_id, func.count(Conversation.id).label("cnt"))
        .group_by(Conversation.user_id)
        .subquery()
    )
    rows = (
        db.query(User, func.coalesce(conv_count.c.cnt, 0).label("conversation_count"))
        .outerjoin(conv_count, User.id == conv_count.c.user_id)
        .order_by(User.full_name)
        .all()
    )
    result = []
    for user, count in rows:
        user.conversation_count = count
        result.append(user)
    return result


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Validate enums
    if data.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {data.role}")
    if data.department not in [d.value for d in Department]:
        raise HTTPException(
            status_code=400, detail=f"Departamento inválido: {data.department}"
        )

    # Check unique constraints
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username ya registrado")

    # Vendedor role is locked to ventas department
    dept = "ventas" if data.role == "vendedor" else data.department

    # Check ad_user_id uniqueness if provided
    if data.ad_user_id:
        if db.query(User).filter(User.ad_user_id == data.ad_user_id).first():
            raise HTTPException(
                status_code=400,
                detail=f"ad_user_id {data.ad_user_id} ya está vinculado a otro usuario",
            )

    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=UserRole(data.role),
        department=Department(dept),
        extra_departments=data.extra_departments,
        allowed_org_ids=data.allowed_org_ids,
        ad_user_id=data.ad_user_id,
        idempiere_salesrep_id=data.idempiere_salesrep_id,
        sensitivity_level=data.sensitivity_level,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/salesreps", tags=["Usuarios"])
def list_salesreps(
    admin: User = Depends(require_admin),
):
    """List salespeople from iDempiere for vendedor role assignment."""
    try:
        db = IdempiereSession()
        try:
            result = db.execute(
                text(
                    "SELECT DISTINCT i.salesrep_id AS id, bp.name "
                    "FROM adempiere.c_invoice i "
                    "JOIN adempiere.c_bpartner bp ON i.salesrep_id = bp.c_bpartner_id "
                    "WHERE i.issotrx = 'Y' AND i.docstatus = 'CO' "
                    "AND i.salesrep_id IS NOT NULL "
                    "AND bp.isactive = 'Y' "
                    "ORDER BY bp.name"
                )
            )
            return [
                {"id": r[0], "name": r[1]}
                for r in result.fetchall()
            ]
        finally:
            db.close()
    except Exception as e:
        logger.error("Error querying iDempiere salesreps: %s", e)
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a iDempiere para obtener los vendedores",
        )


@router.get("/organizations", tags=["Usuarios"])
def list_organizations(
    admin: User = Depends(require_admin),
):
    """List available organizations from iDempiere for user assignment."""
    try:
        db = IdempiereSession()
        try:
            result = db.execute(
                text(
                    "SELECT ad_org_id, value, name "
                    "FROM adempiere.ad_org "
                    "WHERE isactive = 'Y' AND ad_org_id > 0 "
                    "ORDER BY name"
                )
            )
            return [
                {"id": r[0], "value": r[1], "name": r[2]}
                for r in result.fetchall()
            ]
        finally:
            db.close()
    except Exception as e:
        logger.error("Error querying iDempiere organizations: %s", e)
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a iDempiere para obtener las organizaciones",
        )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Verify admin password first
    if not verify_password(data.admin_password, admin.hashed_password):
        raise HTTPException(
            status_code=403, detail="Contraseña de administrador incorrecta"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_data = data.model_dump(exclude_unset=True)

    # Remove non-model fields
    update_data.pop("admin_password", None)
    new_password = update_data.pop("new_password", None)

    if "role" in update_data:
        if update_data["role"] not in [r.value for r in UserRole]:
            raise HTTPException(status_code=400, detail="Rol inválido")
        update_data["role"] = UserRole(update_data["role"])

    if "department" in update_data:
        if update_data["department"] not in [d.value for d in Department]:
            raise HTTPException(status_code=400, detail="Departamento inválido")
        update_data["department"] = Department(update_data["department"])

    # Check email uniqueness if changed
    if "email" in update_data and update_data["email"] != user.email:
        if db.query(User).filter(User.email == update_data["email"]).first():
            raise HTTPException(status_code=400, detail="Email ya registrado")

    # Check ad_user_id uniqueness if changed
    if "ad_user_id" in update_data and update_data["ad_user_id"] != user.ad_user_id:
        if update_data["ad_user_id"] is not None:
            existing = db.query(User).filter(
                User.ad_user_id == update_data["ad_user_id"],
                User.id != user_id,
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"ad_user_id {update_data['ad_user_id']} ya vinculado a {existing.username}",
                )

    for key, value in update_data.items():
        setattr(user, key, value)

    # Handle password change
    if new_password:
        user.hashed_password = hash_password(new_password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.id == admin.id:
        raise HTTPException(
            status_code=400, detail="No puede eliminarse a sí mismo"
        )

    db.delete(user)
    db.commit()
    return {"detail": "Usuario eliminado"}
