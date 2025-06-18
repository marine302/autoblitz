"""
베이스 모델과 공통 Mixin 정의
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from app.core.database import Base


class TimestampMixin:
    """
    타임스탬프 믹스인 - 모든 모델에 공통으로 사용되는 생성/수정 시간 필드

    Attributes:
        created_at: UTC 기준 레코드 생성 시간
        updated_at: UTC 기준 레코드 마지막 수정 시간
    """
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# Base는 database.py에서 가져옴, 여기서는 재정의하지 않음
# 모든 모델은 이 Base를 상속받아 사용
__all__ = ['Base', 'TimestampMixin']
