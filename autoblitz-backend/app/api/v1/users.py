"""
사용자 관리 API
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()


@router.get("/me")
async def get_current_user():
    """현재 사용자 정보 조회 (더미)"""
    return {
        "id": 1,
        "email": "test@example.com",
        "name": "테스트 사용자",
        "plan": "standard",
        "is_active": True,
        "created_at": "2025-06-17T00:00:00Z"
    }


@router.put("/me")
async def update_user(name: Optional[str] = None):
    """사용자 정보 수정 (더미)"""
    return {
        "message": "사용자 정보 수정 완료",
        "user": {
            "id": 1,
            "email": "test@example.com",
            "name": name or "테스트 사용자",
            "plan": "standard"
        }
    }


@router.post("/me/change-password")
async def change_password(
    current_password: Optional[str] = None,
    new_password: Optional[str] = None
):
    """비밀번호 변경 (더미)"""
    return {
        "message": "비밀번호 변경 완료"
    }


@router.get("/me/api-keys")
async def get_api_keys():
    """API 키 목록 조회 (더미)"""
    return {
        "okx": {
            "api_key": "***********ABC",
            "passphrase": "***********123"
        },
        "upbit": {
            "access_key": "***********XYZ"
        }
    }


@router.put("/me/api-keys")
async def update_api_keys(
    exchange: Optional[str] = None,
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None
):
    """API 키 업데이트 (더미)"""
    return {
        "message": f"{exchange} API 키 업데이트 완료"
    }


@router.get("/me/subscription")
async def get_subscription():
    """구독 정보 조회 (더미)"""
    return {
        "plan": "standard",
        "price": 199000,
        "max_bots": 10,
        "period": "monthly",
        "next_billing_date": "2025-07-17",
        "is_active": True
    }
