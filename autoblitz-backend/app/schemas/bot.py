"""
봇 관련 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class BotBase(BaseModel):
    """봇 기본 스키마"""
    name: Optional[str] = None
    strategy_id: str
    exchange: str
    trading_type: str = "spot"
    symbol: str
    initial_amount: float = Field(..., gt=0)

class BotCreate(BotBase):
    """봇 생성 스키마"""
    leverage: Optional[int] = Field(1, ge=1, le=100)
    margin_mode: Optional[str] = None
    position_side: Optional[str] = None
    stop_loss_rate: float = Field(-10.0, le=0)
    profit_target_rate: float = Field(5.0, gt=0)
    auto_coin_change: bool = True

class BotUpdate(BaseModel):
    """봇 수정 스키마"""
    name: Optional[str] = None
    stop_loss_rate: Optional[float] = None
    profit_target_rate: Optional[float] = None
    auto_coin_change: Optional[bool] = None

class BotResponse(BotBase):
    """봇 응답 스키마"""
    id: str
    user_id: str
    current_amount: float
    status: str
    settings: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BotStatisticsResponse(BaseModel):
    """봇 통계 응답 스키마"""
    bot_id: str
    total_trades: int
    successful_trades: int
    total_profit: float
    total_loss: float
    win_rate: float
    average_profit_rate: float
    
    class Config:
        from_attributes = True