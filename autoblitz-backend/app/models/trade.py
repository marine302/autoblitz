"""
거래 관련 모델
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Trade(Base, TimestampMixin):
    """거래 내역을 저장하는 모델"""
    __tablename__ = "trades"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    # 거래 상세 정보
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    profit = Column(Float, default=0.0)

    # 거래 순서/시간 정보
    cycle_number = Column(Integer, default=0)
    executed_at = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))

    # 관계 설정
    bot = relationship("Bot", back_populates="trades")
    user = relationship("User", back_populates="trades")

    def __repr__(self):
        """모델의 문자열 표현"""
        return (
            f"<Trade(id={self.id}, bot_id={self.bot_id}, "
            f"symbol='{self.symbol}', side='{self.side}', "
            f"price={self.price}, profit={self.profit})>"
        )


class GridOrder(Base, TimestampMixin):
    """그리드 주문 테이블 (단타로 전략)"""
    __tablename__ = "grid_orders"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    bot_id = Column(String(50), ForeignKey("bots.id"), nullable=False)

    # 그리드 정보
    grid_level = Column(Integer, nullable=False)  # 그리드 레벨 (1~7)
    order_type = Column(String(10), nullable=False)  # buy/sell

    # 주문 정보
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    order_id = Column(String(100))

    # 상태
    # pending/placed/filled/cancelled
    status = Column(String(20), default="pending")
    filled_at = Column(DateTime(timezone=True))

    # 연결된 주문 (매수-매도 쌍)
    paired_order_id = Column(Integer, ForeignKey("grid_orders.id"))

    def __repr__(self):
        return f"<GridOrder(id={self.id}, bot_id={self.bot_id}, level={self.grid_level}, type={self.order_type})>"
