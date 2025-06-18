"""
사용자 모델
"""

from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from ..core.database import Base
from .base import TimestampMixin


class User(Base, TimestampMixin):
    """사용자 테이블"""
    __tablename__ = "users"

    # Primary Key
    id = Column(String(50), primary_key=True, index=True)

    # 기본 정보
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # 프로필
    name = Column(String(100))
    phone = Column(String(20))

    # 요금제
    # lite, standard, pro, enterprise
    plan_id = Column(String(20), default="lite")

    # 상태
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # 설정
    preferred_exchange = Column(String(20), default="okx")  # okx, upbit

    # OKX API 키 필드들
    okx_api_key = Column(String(255), nullable=True)
    okx_secret_key = Column(String(255), nullable=True)
    okx_passphrase = Column(String(255), nullable=True)

    # 업비트 API 키 필드들
    upbit_access_key = Column(String(255), nullable=True)
    upbit_secret_key = Column(String(255), nullable=True)

    # 관계
    bots = relationship("Bot", back_populates="user",
                        cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"
