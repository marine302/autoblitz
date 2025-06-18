"""
사용자 관련 스키마
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """사용자 기본 스키마"""
    email: EmailStr
    name: Optional[str] = None
    preferred_exchange: str = "okx"

class UserCreate(UserBase):
    """사용자 생성 스키마"""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """사용자 수정 스키마"""
    name: Optional[str] = None
    phone: Optional[str] = None
    preferred_exchange: Optional[str] = None

class UserResponse(UserBase):
    """사용자 응답 스키마"""
    id: str
    plan_id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """로그인 스키마"""
    email: EmailStr
    password: str

class Token(BaseModel):
    """토큰 스키마"""
    access_token: str
    token_type: str = "bearer"