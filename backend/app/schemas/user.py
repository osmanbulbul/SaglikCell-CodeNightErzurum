from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserBase(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    chronic_conditions: Optional[str] = None

class UserCreate(UserBase):
    pass # Password will be handled internally for OTP flow

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    chronic_conditions: Optional[str] = None

class UserInDBBase(UserBase):
    id: UUID
    role: UserRole

    class Config:
        from_attributes = True

class UserResponse(UserInDBBase):
    pass
