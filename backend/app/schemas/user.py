import re
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


PASSWORD_POLICY_MSG = (
    "La contraseña debe tener mínimo 8 caracteres, "
    "una mayúscula, una minúscula, un número y un carácter especial (!@#$%^&*)"
)

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def validate_password_strength(password: str) -> str:
    if not _PASSWORD_RE.match(password):
        raise ValueError(PASSWORD_POLICY_MSG)
    return password


class UserLogin(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: str = "usuario"
    department: str
    extra_departments: str | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    department: str | None = None
    extra_departments: str | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    department: str
    extra_departments: str | None
    is_active: bool
    avatar_url: str | None = None
    totp_enabled: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    totp_required: bool = False


class TokenData(BaseModel):
    user_id: int | None = None
    username: str | None = None
    role: str | None = None
    department: str | None = None


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_uri: str


class TOTPVerify(BaseModel):
    totp_code: str
