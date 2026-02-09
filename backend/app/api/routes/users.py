from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.models.user import User, UserRole, Department
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/", response_model=list[UserResponse])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.full_name).all()


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

    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=UserRole(data.role),
        department=Department(data.department),
        extra_departments=data.extra_departments,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_data = data.model_dump(exclude_unset=True)

    if "role" in update_data:
        if update_data["role"] not in [r.value for r in UserRole]:
            raise HTTPException(status_code=400, detail="Rol inválido")
        update_data["role"] = UserRole(update_data["role"])

    if "department" in update_data:
        if update_data["department"] not in [d.value for d in Department]:
            raise HTTPException(status_code=400, detail="Departamento inválido")
        update_data["department"] = Department(update_data["department"])

    for key, value in update_data.items():
        setattr(user, key, value)

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
