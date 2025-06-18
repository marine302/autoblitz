# app/bot_engine/executors/strategy_executor.py

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class StrategySignal:
    """전략 신호"""
    action: str  # "BUY", "SELL", "HOLD"
    price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    order_type: str = "LIMIT"  # "LIMIT", "MARKET"
    reason: str = ""
    confidence: float = 1.0  # 신호 신뢰도 (0.0 ~ 1.0)
    
    # 단타로 전략 전용 필드들
    grid_level: Optional[int] = None  # 그리드 레벨 (1~7)
    target_profit_price: Optional[Decimal] = None  # 목표 익절가
    stop_loss_price: Optional[Decimal] = None  # 손절가
    
@dataclass
class MarketCondition:
    """시장 상황 분석 결과"""
    trend: str  # "UP", "DOWN", "SIDEWAYS"
    volatility: float  # 변동성 (0.0 ~ 1.0)
    volume_strength: float  # 거래량 강도 (0.0 ~ 1.0)
    support_level: Optional[Decimal] = None
    resistance_level: Optional[Decimal] = None

class StrategyExecutor:
    """전략 실행기 - 전략 로직을 실행하고 매매 신호를 생성"""
    
    def __init__(self, strategy_name: str, exchange_client, symbol: str, settings: Dict[str, Any]):
        self.strategy_name = strategy_name
        self.exchange_client = exchange_client
        self.symbol = symbol
        self.settings = settings
        
        # 전략별 설정값들
        self.profit_target = Decimal(str(settings.get('profit_target', 0.5)))  # 기본 0.5%
        self.stop_loss = Decimal(str(settings.get('stop_loss', -10.0)))  # 기본 -10%
        self.grid_levels = settings.get('grid_levels', 7)  # 기본 7단계
        self.base_amount = Decimal(str(settings.get('base_amount', 10.0)))  # 기본 $10
        self.multiplier = Decimal(str(settings.get('multiplier', 2.0)))  # 기본 2배수
        
        # 상태 추적
        self.last_analysis_time = None
        self.market_condition = None
        self.recent_signals = []  # 최근 신호 이력
        
        # 전략별 핸들러 매핑
        self.strategy_handlers = {
            'dantaro': self._execute_dantaro_strategy,
            'scalping': self._execute_scalping_strategy,
            'grid': self._execute_grid_strategy
        }
        
    async def initialize(self):
        """전략 초기화"""
        try:
            logger.info(f"전략 {self.strategy_name} 초기화 시작")
            
            # 전략별 초기화
            if self.strategy_name == 'dantaro':
                await self._initialize_dantaro()
            elif self.strategy_name == 'scalping':
                await self._initialize_scalping()
            elif self.strategy_name == 'grid':
                await self._initialize_grid()
            else:
                logger.warning(f"알 수 없는 전략: {self.strategy_name}")
                
            logger.info(f"전략 {self.strategy_name} 초기화 완료")
            
        except Exception as e:
            logger.error(f"전략 초기화 실패: {e}")
            raise
    
    async def get_signal(self, current_price: Decimal, position: Dict, market_data: Dict) -> StrategySignal:
        """매매 신호 생성 - 메인 엔트리 포인트"""
        try:
            # 시장 상황 분석
            await self._analyze_market_condition(current_price, market_data)
            
            # 전략별 신호 생성
            handler = self.strategy_handlers.get(self.strategy_name)
            if handler:
                signal = await handler(current_price, position, market_data)
            else:
                signal = StrategySignal(action="HOLD", reason="지원하지 않는 전략")
            
            # 신호 이력 저장
            self._save_signal_history(signal)
            
            # 신호 로깅
            if signal.action != "HOLD":
                logger.info(f"전략 신호: {signal.action} {signal.quantity} {self.symbol} @ {signal.price} ({signal.reason})")
            
            return signal
            
        except Exception as e:
            logger.error(f"신호 생성 실패: {e}")
            return StrategySignal(action="HOLD", reason=f"오류 발생: {str(e)}")
    
    # ===== 단타로 전략 구현 =====
    
    async def _initialize_dantaro(self):
        """단타로 전략 초기화"""
        logger.info("단타로 전략 초기화: 7단계 그리드 물타기 전략")
        
        # 단타로 전략 설정 검증
        required_settings = ['capital', 'profit_target', 'grid_levels']
        for setting in required_settings:
            if setting not in self.settings:
                raise ValueError(f"단타로 전략에 필요한 설정 누락: {setting}")
        
        # 그리드 레벨별 금액 계산
        self.grid_amounts = self._calculate_grid_amounts()
        logger.info(f"그리드 금액 설정: {self.grid_amounts}")
    
    async def _execute_dantaro_strategy(self, current_price: Decimal, position: Dict, market_data: Dict) -> StrategySignal:
        """단타로 전략 실행"""
        
        # 현재 포지션 분석
        current_grid_level = position.get('grid_level', 0)
        total_invested = position.get('total_invested', 0)
        average_price = position.get('average_price', 0)
        total_quantity = position.get('total_quantity', 0)
        
        # 1. 포지션이 없을 때 - 첫 매수
        if current_grid_level == 0:
            return await self._dantaro_initial_buy(current_price)
        
        # 2. 포지션이 있을 때 - 추가 매수 또는 매도 판단
        else:
            # 익절 조건 확인
            if self._should_take_profit(current_price, average_price):
                return await self._dantaro_sell_signal(current_price, total_quantity, average_price)
            
            # 추가 매수 조건 확인 (물타기)
            elif self._should_add_position(current_price, position):
                return await self._dantaro_add_buy_signal(current_price, current_grid_level)
            
            # 손절 조건 확인
            elif self._should_stop_loss(current_price, position):
                return await self._dantaro_stop_loss_signal(current_price, total_quantity)
            
            else:
                return StrategySignal(action="HOLD", reason="단타로 대기 중")
    
    async def _dantaro_initial_buy(self, current_price: Decimal) -> StrategySignal:
        """단타로 첫 매수 신호"""
        # 1단계 매수 금액 (기본 금액)
        buy_amount_usdt = self.grid_amounts[0]
        quantity = buy_amount_usdt / current_price
        
        return StrategySignal(
            action="BUY",
            price=current_price,
            quantity=quantity,
            order_type="MARKET",
            reason="단타로 1단계 매수",
            grid_level=1,
            target_profit_price=current_price * (1 + self.profit_target / 100)
        )
    
    async def _dantaro_add_buy_signal(self, current_price: Decimal, current_level: int) -> StrategySignal:
        """단타로 추가 매수 신호 (물타기)"""
        next_level = current_level + 1
        
        if next_level > self.grid_levels:
            return StrategySignal(action="HOLD", reason="최대 그리드 레벨 도달")
        
        # 다음 단계 매수 금액
        buy_amount_usdt = self.grid_amounts[next_level - 1]
        quantity = buy_amount_usdt / current_price
        
        return StrategySignal(
            action="BUY",
            price=current_price,
            quantity=quantity,
            order_type="MARKET",
            reason=f"단타로 {next_level}단계 물타기",
            grid_level=next_level
        )
    
    async def _dantaro_sell_signal(self, current_price: Decimal, total_quantity: Decimal, average_price: Decimal) -> StrategySignal:
        """단타로 익절 매도 신호"""
        return StrategySignal(
            action="SELL",
            price=current_price,
            quantity=total_quantity,
            order_type="MARKET",
            reason=f"단타로 익절 (수익률: {((current_price - average_price) / average_price * 100):.2f}%)",
            grid_level=0  # 포지션 리셋
        )
    
    async def _dantaro_stop_loss_signal(self, current_price: Decimal, total_quantity: Decimal) -> StrategySignal:
        """단타로 손절 매도 신호"""
        return StrategySignal(
            action="SELL",
            price=current_price,
            quantity=total_quantity,
            order_type="MARKET",
            reason="단타로 손절",
            grid_level=0  # 포지션 리셋
        )
    
    def _calculate_grid_amounts(self) -> List[Decimal]:
        """그리드별 매수 금액 계산 (1, 2, 4, 8, 16, 32, 64 배수)"""
        amounts = []
        base_amount = self.base_amount
        
        for level in range(self.grid_levels):
            amount = base_amount * (self.multiplier ** level)
            amounts.append(amount)
        
        return amounts
    
    def _should_take_profit(self, current_price: Decimal, average_price: Decimal) -> bool:
        """익절 조건 확인"""
        if average_price <= 0:
            return False
            
        profit_rate = (current_price - average_price) / average_price * 100
        return profit_rate >= self.profit_target
    
    def _should_add_position(self, current_price: Decimal, position: Dict) -> bool:
        """추가 매수 조건 확인 (하락률 기준)"""
        last_buy_price = position.get('last_buy_price', 0)
        current_level = position.get('grid_level', 0)
        
        if last_buy_price <= 0 or current_level >= self.grid_levels:
            return False
        
        # 마지막 매수가 대비 일정 비율 하락 시 추가 매수
        drop_threshold = Decimal('2.0')  # 2% 하락 시 추가 매수
        drop_rate = (last_buy_price - current_price) / last_buy_price * 100
        
        return drop_rate >= drop_threshold
    
    def _should_stop_loss(self, current_price: Decimal, position: Dict) -> bool:
        """손절 조건 확인"""
        average_price = position.get('average_price', 0)
        
        if average_price <= 0:
            return False
            
        loss_rate = (current_price - average_price) / average_price * 100
        return loss_rate <= self.stop_loss
    
    # ===== 기타 전략들 (스켈레톤) =====
    
    async def _initialize_scalping(self):
        """스캘핑 전략 초기화"""
        logger.info("스캘핑 전략 초기화")
        pass
    
    async def _execute_scalping_strategy(self, current_price: Decimal, position: Dict, market_data: Dict) -> StrategySignal:
        """스캘핑 전략 실행"""
        return StrategySignal(action="HOLD", reason="스캘핑 전략 구현 예정")
    
    async def _initialize_grid(self):
        """그리드 전략 초기화"""
        logger.info("그리드 전략 초기화")
        pass
    
    async def _execute_grid_strategy(self, current_price: Decimal, position: Dict, market_data: Dict) -> StrategySignal:
        """그리드 전략 실행"""
        return StrategySignal(action="HOLD", reason="그리드 전략 구현 예정")
    
    # ===== 시장 분석 =====
    
    async def _analyze_market_condition(self, current_price: Decimal, market_data: Dict):
        """시장 상황 분석"""
        try:
            ticker = market_data.get('ticker', {})
            orderbook = market_data.get('orderbook', {})
            
            # 기본 시장 상황 분석
            high_24h = Decimal(str(ticker.get('high', current_price)))
            low_24h = Decimal(str(ticker.get('low', current_price)))
            volume_24h = Decimal(str(ticker.get('volume', 0)))
            
            # 변동성 계산
            volatility = float((high_24h - low_24h) / current_price) if current_price > 0 else 0
            
            # 트렌드 분석 (간단한 버전)
            mid_price = (high_24h + low_24h) / 2
            if current_price > mid_price * Decimal('1.02'):
                trend = "UP"
            elif current_price < mid_price * Decimal('0.98'):
                trend = "DOWN"
            else:
                trend = "SIDEWAYS"
            
            # 거래량 강도 (정규화된 값)
            volume_strength = min(float(volume_24h) / 1000000, 1.0)  # 간단한 정규화
            
            self.market_condition = MarketCondition(
                trend=trend,
                volatility=volatility,
                volume_strength=volume_strength,
                support_level=low_24h,
                resistance_level=high_24h
            )
            
            self.last_analysis_time = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"시장 분석 실패: {e}")
            # 기본값 설정
            self.market_condition = MarketCondition(
                trend="SIDEWAYS",
                volatility=0.1,
                volume_strength=0.5
            )
    
    def _save_signal_history(self, signal: StrategySignal):
        """신호 이력 저장"""
        signal_record = {
            'timestamp': datetime.now(timezone.utc),
            'action': signal.action,
            'price': float(signal.price) if signal.price else None,
            'quantity': float(signal.quantity) if signal.quantity else None,
            'reason': signal.reason,
            'grid_level': signal.grid_level
        }
        
        self.recent_signals.append(signal_record)
        
        # 최근 100개 신호만 유지
        if len(self.recent_signals) > 100:
            self.recent_signals = self.recent_signals[-100:]
    
    def get_strategy_stats(self) -> Dict:
        """전략 통계 정보"""
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'settings': dict(self.settings),
            'market_condition': {
                'trend': self.market_condition.trend if self.market_condition else 'UNKNOWN',
                'volatility': self.market_condition.volatility if self.market_condition else 0.0,
                'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None
            },
            'recent_signals_count': len(self.recent_signals),
            'last_signal': self.recent_signals[-1] if self.recent_signals else None
        }
    
    async def cleanup(self):
        """정리 작업"""
        logger.info(f"전략 {self.strategy_name} 정리 작업")
        self.recent_signals.clear()


# ===== 전략 팩토리 =====

def create_strategy_executor(strategy_name: str, exchange_client, symbol: str, settings: Dict[str, Any]) -> StrategyExecutor:
    """전략 실행기 팩토리 함수"""
    return StrategyExecutor(strategy_name, exchange_client, symbol, settings)


# ===== 테스트 함수 =====

async def test_dantaro_strategy():
    """단타로 전략 테스트"""
    print("=== 단타로 전략 테스트 ===")
    
    # 테스트 설정
    settings = {
        'capital': 1000.0,
        'profit_target': 0.5,
        'stop_loss': -10.0,
        'grid_levels': 7,
        'base_amount': 10.0,
        'multiplier': 2.0
    }
    
    # 전략 실행기 생성
    executor = StrategyExecutor('dantaro', None, 'BTC/USDT', settings)
    await executor.initialize()
    
    # 테스트 시나리오
    current_price = Decimal('50000')
    
    # 1. 첫 매수 신호
    position = {'grid_level': 0}
    market_data = {
        'ticker': {'high': 52000, 'low': 48000, 'volume': 1000},
        'orderbook': {}
    }
    
    signal1 = await executor.get_signal(current_price, position, market_data)
    print(f"첫 매수 신호: {signal1}")
    
    # 2. 추가 매수 신호 (가격 하락)
    position = {
        'grid_level': 1,
        'last_buy_price': 50000,
        'average_price': 50000,
        'total_quantity': 0.0002
    }
    current_price = Decimal('49000')  # 2% 하락
    
    signal2 = await executor.get_signal(current_price, position, market_data)
    print(f"추가 매수 신호: {signal2}")
    
    # 3. 익절 신호 (가격 상승)
    position = {
        'grid_level': 2,
        'average_price': 49500,
        'total_quantity': 0.0006
    }
    current_price = Decimal('49750')  # 0.5% 상승
    
    signal3 = await executor.get_signal(current_price, position, market_data)
    print(f"익절 신호: {signal3}")
    
    # 통계 출력
    stats = executor.get_strategy_stats()
    print(f"전략 통계: {stats}")


if __name__ == "__main__":
    asyncio.run(test_dantaro_strategy())