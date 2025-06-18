# app/models/bot.py (완전히 새로 작성)

import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Enum as SQLEnum
from datetime import datetime, timezone

from app.core.database import Base

class BotStatus(enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String(100), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    strategy = Column(String(50), nullable=False)
    capital = Column(Float, nullable=False)
    status = Column(SQLEnum(BotStatus), default=BotStatus.CREATED, nullable=False)
    settings = Column(JSON, nullable=True)
    
    # 시간 필드들
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    
    # 에러 관련
    error_message = Column(Text, nullable=True)
    
    # 통계 필드들
    total_profit = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)