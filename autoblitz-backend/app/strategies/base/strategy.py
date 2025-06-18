"""
거래 전략 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel

class Signal(BaseModel):
    """거래 신호"""
    action: str  # buy/sell/hold
    symbol: str
    price: float
    amount: float
    reason: str
    confidence: float = 1.0  # 0~1
    metadata: Dict[str, Any] = {}

class StrategyState(BaseModel):
    """전략 상태"""
    is_active: bool = True
    position: float = 0.0  # 현재 포지션
    entry_price: Optional[float] = None
    last_signal: Optional[Signal] = None
    last_update: datetime = datetime.utcnow()
    custom_data: Dict[str, Any] = {}

class BaseStrategy(ABC):
    """거래 전략 기본 클래스"""
    
    def __init__(self, bot_config: Dict[str, Any]):
        self.bot_id = bot_config.get("bot_id")
        self.symbol = bot_config.get("symbol")
        self.initial_amount = bot_config.get("initial_amount")
        self.config = bot_config
        self.state = StrategyState()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """전략 이름"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """전략 설명"""
        pass
    
    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """시장 분석 및 신호 생성"""
        pass
    
    @abstractmethod
    async def on_order_filled(self, order: Dict[str, Any]) -> None:
        """주문 체결 시 처리"""
        pass
    
    @abstractmethod
    async def on_error(self, error: Exception) -> None:
        """에러 발생 시 처리"""
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return self.state.dict()
    
    def update_state(self, updates: Dict[str, Any]) -> None:
        """상태 업데이트"""
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.last_update = datetime.utcnow()