"""
인증 관련 API
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()


@router.post("/login")
async def login(email: Optional[str] = None, password: Optional[str] = None):
    """로그인 (더미)"""
    return {
        "message": "로그인 성공",
        "access_token": "dummy.access.token",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "email": email or "test@example.com",
            "name": "테스트 사용자"
        }
    }


@router.post("/register")
async def register(email: Optional[str] = None, password: Optional[str] = None):
    """회원가입 (더미)"""
    return {
        "message": "회원가입 성공",
        "user": {
            "id": 1,
            "email": email or "test@example.com",
            "name": "테스트 사용자"
        }
    }


@router.post("/logout")
async def logout():
    """로그아웃 (더미)"""
    return {
        "message": "로그아웃 성공"
    }


@router.post("/refresh")
async def refresh_token():
    """토큰 갱신 (더미)"""
    return {
        "message": "토큰 갱신 성공",
        "access_token": "dummy.new.token",
        "token_type": "bearer"
    }


@router.post("/verify-email")
async def verify_email(token: Optional[str] = None):
    """이메일 인증 (더미)"""
    return {
        "message": "이메일 인증 성공"
    }


@router.post("/reset-password")
async def reset_password(email: Optional[str] = None):
    """비밀번호 재설정 요청 (더미)"""
    return {
        "message": "비밀번호 재설정 이메일 발송 완료"
    }
