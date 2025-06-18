# app/strategies/dantaro/okx_spot_v1.py
"""
단타로 OKX 현물 전략 V1
7단계 그리드 매매 전략
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

class DantaroOKXSpotV1:
    """단타로 OKX 현물 전략"""
    
    def __init__(self, bot_config: Dict[str, Any]):
        # 전략 파라미터
        self.symbol = bot_config['symbol']
        self.capital = float(bot_config.get("capital", 100.0))
        self.grid_count = int(bot_config.get("grid_count", 7))
        self.grid_gap = float(bot_config.get("grid_gap", 0.5))
        self.multiplier = float(bot_config.get("multiplier", 2))
        self.profit_target = float(bot_config.get("profit_target", 0.5))
        self.stop_loss = float(bot_config.get("stop_loss", -10.0))
        
        # Calculate initial and base amounts
        self.initial_amount = self.capital
        self.base_amount = self._calculate_base_amount()
        
        # 그리드 상태
        self.grids = self._initialize_grids()
    
    @property
    def name(self) -> str:
        return "단타로 OKX 현물 V1"
    
    @property
    def description(self) -> str:
        return "7단계 그리드를 활용한 단타 매매 전략. 하락 시 분할 매수, 상승 시 분할 매도"
    
    def _calculate_base_amount(self) -> float:
        """기본 주문 금액 계산"""
        if self.grid_count <= 0:
            return 0.0
        
        # 물타기 전략: 1 + 2 + 4 + 8 + 16 + 32 + 64 = 127 비율
        total_ratio = sum(self.multiplier ** i for i in range(self.grid_count))
        return self.initial_amount / total_ratio
    
    def _initialize_grids(self) -> List[Dict[str, Any]]:
        """그리드 초기화"""
        grids = []
        for i in range(self.grid_count):
            grids.append({
                "level": i + 1,
                "buy_price": None,
                "sell_price": None,
                "amount": self.base_amount * (self.multiplier ** i),
                "buy_order_id": None,
                "sell_order_id": None,
                "status": "ready"  # ready/buying/bought/selling/sold
            })
        return grids
    
    def calculate_grid_levels(self, current_price: float) -> Dict[str, List[float]]:
        """현재 가격 기준으로 그리드 레벨 계산"""
        buy_prices = []
        sell_prices = []
        
        for i in range(self.grid_count):
            # 하락 시 매수 가격 (현재가에서 간격만큼 아래)
            buy_price = current_price * (1 - (self.grid_gap / 100) * (i + 1))
            buy_prices.append(buy_price)
            
            # 상승 시 매도 가격 (평균가 기준 이익 목표)
            sell_price = current_price * (1 + (self.profit_target / 100))
            sell_prices.append(sell_price)
        
        return {
            "buy_prices": buy_prices,
            "sell_prices": sell_prices
        }
    
    def should_buy(self, current_price: float, grid_level: int) -> bool:
        """매수 조건 확인"""
        if grid_level >= len(self.grids):
            return False
        
        grid = self.grids[grid_level]
        if grid["status"] != "ready":
            return False
        
        # 그리드 레벨에 해당하는 가격 도달 시 매수
        target_price = current_price * (1 - (self.grid_gap / 100) * (grid_level + 1))
        return current_price <= target_price
    
    def should_sell(self, current_price: float, average_price: float) -> bool:
        """매도 조건 확인"""
        if average_price <= 0:
            return False
        
        # 수익 목표 달성 시 매도
        profit_rate = ((current_price - average_price) / average_price) * 100
        return profit_rate >= self.profit_target
    
    def should_stop_loss(self, current_price: float, average_price: float) -> bool:
        """손절 조건 확인"""
        if average_price <= 0:
            return False
        
        # 손절선 도달 시 강제 매도
        loss_rate = ((current_price - average_price) / average_price) * 100
        return loss_rate <= self.stop_loss
    
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """시장 분석 및 시그널 생성"""
        current_price = float(market_data.get("price", 0))
        
        if current_price <= 0:
            return None
        
        # 기본 시그널 구조
        signal = {
            "strategy": self.name,
            "symbol": self.symbol,
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "action": "HOLD",
            "amount": 0,
            "price": current_price,
            "reason": "조건 대기 중",
            "grid_info": {
                "active_grids": len([g for g in self.grids if g["status"] == "bought"]),
                "total_grids": self.grid_count,
                "next_buy_level": self._get_next_buy_level()
            }
        }
        
        # 매수 시그널 확인
        next_level = self._get_next_buy_level()
        if next_level is not None and self.should_buy(current_price, next_level):
            signal.update({
                "action": "BUY",
                "amount": self.grids[next_level]["amount"],
                "reason": f"그리드 레벨 {next_level + 1} 매수 조건 충족"
            })
        
        # TODO: 매도 시그널 로직 (평균가 계산 필요)
        # TODO: 손절 시그널 로직
        
        return signal
    
    def _get_next_buy_level(self) -> Optional[int]:
        """다음 매수 가능한 그리드 레벨 반환"""
        for i, grid in enumerate(self.grids):
            if grid["status"] == "ready":
                return i
        return None
    
    def update_grid_status(self, level: int, status: str, order_id: str = None):
        """그리드 상태 업데이트"""
        if 0 <= level < len(self.grids):
            self.grids[level]["status"] = status
            if order_id:
                if status in ["buying", "bought"]:
                    self.grids[level]["buy_order_id"] = order_id
                elif status in ["selling", "sold"]:
                    self.grids[level]["sell_order_id"] = order_id
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """전략 정보 반환"""
        return {
            "name": self.name,
            "description": self.description,
            "symbol": self.symbol,
            "capital": self.capital,
            "grid_count": self.grid_count,
            "grid_gap": self.grid_gap,
            "multiplier": self.multiplier,
            "profit_target": self.profit_target,
            "stop_loss": self.stop_loss,
            "initial_amount": self.initial_amount,
            "base_amount": self.base_amount,
            "total_required_capital": sum(grid["amount"] for grid in self.grids),
            "grids": self.grids
        }