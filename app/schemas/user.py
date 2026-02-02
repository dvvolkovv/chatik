"""
User schemas for API
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, UUID4


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""
    password: str


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """User response schema"""
    id: UUID4
    is_active: bool
    is_verified: bool
    balance: float
    created_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
