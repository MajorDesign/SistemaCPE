from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ============================================================
# Schemas: User
# ============================================================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    username: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================
# Schemas: Password
# ============================================================
class PasswordCreate(BaseModel):
    client: str
    email: Optional[str] = None
    description: str
    password: str
    link: Optional[str] = None
    observation: Optional[str] = None
    group_id: Optional[int] = None
    is_public: bool = False

class PasswordUpdate(BaseModel):
    client: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    password: Optional[str] = None
    link: Optional[str] = None
    observation: Optional[str] = None
    group_id: Optional[int] = None
    is_public: Optional[bool] = None

class PasswordResponse(BaseModel):
    id: int
    client: str
    email: Optional[str]
    description: str
    password: str
    link: Optional[str]
    observation: Optional[str]
    group_id: Optional[int]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================
# Schemas: Auth
# ============================================================
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse