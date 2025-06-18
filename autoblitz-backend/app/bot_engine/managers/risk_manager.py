# app/bot_engine/managers/risk_manager.py

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class RiskCheckResult:
    """리스크 체크 결과"""
    should_stop: bool = False
    should_close_position: bool = False
    should_reduce_position: bool = False
    should_pause: bool = False
    reason: str = ""
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

class RiskManager:
    """리스크 관리자 - 봇의 리스크를 모니터링하고 제어"""
    
    def __init__(self, capital: float, settings: Dict[str, Any]):
        self.capital = Decimal(str(capital))
        self.settings = settings
        
        # 리스크 설정값들
        self.max_loss_percentage = Decimal(str(settings.get('max_loss_percentage', -15.0)))  # 최대 손실률
        self.max_drawdown = Decimal(str(settings.get('max_drawdown', -20.0)))  # 최대 드로우다운
        self.max_position_size = Decimal(str(settings.get('max_position_size', 80.0)))  # 최대 포지션 비율
        self.daily_loss_limit = Decimal(str(settings.get('daily_loss_limit', -5.0)))  # 일일 손실 제한
        
        # 거래 빈도 제한
        self.max_trades_per_hour = settings.get('max_trades_per_hour', 10)
        self.max_trades_per_day = settings.get('max_trades_per_day', 100)
        
        # 변동성 임계값
        self.volatility_threshold = Decimal(str(settings.get('volatility_threshold', 5.0)))  # 5% 변동성
        
        # 추적 변수들
        self.daily_pnl = Decimal('0')
        self.peak_balance = self.capital
        self.trade_count_hour = 0
        self.trade_count_day = 0
        self.last_trade_time = None
        self.last_hour_reset = datetime.now(timezone.utc)
        self.last_day_reset = datetime.now(timezone.utc)
        
        # 리스크 이벤트 기록
        self.risk_events = []
        
    async def check_risk(self, current_price: Decimal, position: Dict, total_profit: Decimal) -> RiskCheckResult:
        """종합 리스크 체크"""
        try:
            # 시간 기반 카운터 리셋
            await self._reset_time_counters()
            
            # 1. 손실률 체크
            loss_check = await self._check_loss_limits(total_profit)
            if loss_check.should_stop:
                return loss_check
            
            # 2. 포지션 크기 체크
            position_check = await self._check_position_size(position)
            if position_check.should_reduce_position:
                return position_check
            
            # 3. 거래 빈도 체크
            frequency_check = await self._check_trading_frequency()
            if frequency_check.should_pause:
                return frequency_check
            
            # 4. 시장 변동성 체크
            volatility_check = await self._check_market_volatility(current_price)
            if volatility_check.should_pause:
                return volatility_check
            
            # 5. 드로우다운 체크
            drawdown_check = await self._check_drawdown(total_profit)
            if drawdown_check.should_stop:
                return drawdown_check
            
            # 모든 체크 통과
            return RiskCheckResult(reason="모든 리스크 체크 통과")
            
        except Exception as e:
            logger.error(f"리스크 체크 중 오류: {e}")
            return RiskCheckResult(
                should_pause=True,
                reason=f"리스크 체크 오류: {str(e)}",
                severity="HIGH"
            )
    
    async def _check_loss_limits(self, total_profit: Decimal) -> RiskCheckResult:
        """손실 한계 체크"""
        try:
            # 총 손실률 계산
            loss_percentage = (total_profit / self.capital * 100) if self.capital > 0 else Decimal('0')
            
            # 최대 손실률 초과 체크
            if loss_percentage <= self.max_loss_percentage:
                self._log_risk_event("CRITICAL", f"최대 손실률 초과: {loss_percentage}%")
                return RiskCheckResult(
                    should_stop=True,
                    reason=f"최대 손실률 {self.max_loss_percentage}% 초과 (현재: {loss_percentage}%)",
                    severity="CRITICAL"
                )
            
            # 일일 손실 한계 체크
            daily_loss_percentage = (self.daily_pnl / self.capital * 100) if self.capital > 0 else Decimal('0')
            if daily_loss_percentage <= self.daily_loss_limit:
                self._log_risk_event("HIGH", f"일일 손실 한계 초과: {daily_loss_percentage}%")
                return RiskCheckResult(
                    should_pause=True,
                    reason=f"일일 손실 한계 {self.daily_loss_limit}% 초과 (현재: {daily_loss_percentage}%)",
                    severity="HIGH"
                )
            
            return RiskCheckResult(reason="손실 한계 체크 통과")
            
        except Exception as e:
            logger.error(f"손실 한계 체크 실패: {e}")
            return RiskCheckResult(reason="손실 한계 체크 오류")
    
    async def _check_position_size(self, position: Dict) -> RiskCheckResult:
        """포지션 크기 체크"""
        try:
            total_cost = Decimal(str(position.get('total_cost', 0)))
            
            # 포지션 비율 계산
            position_percentage = (total_cost / self.capital * 100) if self.capital > 0 else Decimal('0')
            
            if position_percentage > self.max_position_size:
                self._log_risk_event("MEDIUM", f"포지션 크기 과다: {position_percentage}%")
                return RiskCheckResult(
                    should_reduce_position=True,
                    reason=f"포지션 크기 {self.max_position_size}% 초과 (현재: {position_percentage}%)",
                    severity="MEDIUM"
                )
            
            return RiskCheckResult(reason="포지션 크기 체크 통과")
            
        except Exception as e:
            logger.error(f"포지션 크기 체크 실패: {e}")
            return RiskCheckResult(reason="포지션 크기 체크 오류")
    
    async def _check_trading_frequency(self) -> RiskCheckResult:
        """거래 빈도 체크"""
        try:
            # 시간당 거래 횟수 체크
            if self.trade_count_hour >= self.max_trades_per_hour:
                self._log_risk_event("MEDIUM", f"시간당 거래 한계 도달: {self.trade_count_hour}회")
                return RiskCheckResult(
                    should_pause=True,
                    reason=f"시간당 거래 한계 {self.max_trades_per_hour}회 초과",
                    severity="MEDIUM"
                )
            
            # 일일 거래 횟수 체크
            if self.trade_count_day >= self.max_trades_per_day:
                self._log_risk_event("HIGH", f"일일 거래 한계 도달: {self.trade_count_day}회")
                return RiskCheckResult(
                    should_pause=True,
                    reason=f"일일 거래 한계 {self.max_trades_per_day}회 초과",
                    severity="HIGH"
                )
            
            return RiskCheckResult(reason="거래 빈도 체크 통과")
            
        except Exception as e:
            logger.error(f"거래 빈도 체크 실패: {e}")
            return RiskCheckResult(reason="거래 빈도 체크 오류")
    
    async def _check_market_volatility(self, current_price: Decimal) -> RiskCheckResult:
        """시장 변동성 체크"""
        try:
            # 간단한 변동성 체크 (실제로는 더 복잡한 로직 필요)
            if hasattr(self, 'last_price') and self.last_price:
                price_change = abs(current_price - self.last_price) / self.last_price * 100
                
                if price_change > self.volatility_threshold:
                    self._log_risk_event("MEDIUM", f"높은 변동성 감지: {price_change}%")
                    return RiskCheckResult(
                        should_pause=True,
                        reason=f"높은 변동성 감지 (임계값 {self.volatility_threshold}%, 현재: {price_change}%)",
                        severity="MEDIUM"
                    )
            
            self.last_price = current_price
            return RiskCheckResult(reason="변동성 체크 통과")
            
        except Exception as e:
            logger.error(f"변동성 체크 실패: {e}")
            return RiskCheckResult(reason="변동성 체크 오류")
    
    async def _check_drawdown(self, total_profit: Decimal) -> RiskCheckResult:
        """드로우다운 체크"""
        try:
            current_balance = self.capital + total_profit
            
            # 최고점 업데이트
            if current_balance > self.peak_balance:
                self.peak_balance = current_balance
            
            # 드로우다운 계산
            drawdown = (current_balance - self.peak_balance) / self.peak_balance * 100
            
            if drawdown <= self.max_drawdown:
                self._log_risk_event("CRITICAL", f"최대 드로우다운 초과: {drawdown}%")
                return RiskCheckResult(
                    should_stop=True,
                    reason=f"최대 드로우다운 {self.max_drawdown}% 초과 (현재: {drawdown}%)",
                    severity="CRITICAL"
                )
            
            return RiskCheckResult(reason="드로우다운 체크 통과")
            
        except Exception as e:
            logger.error(f"드로우다운 체크 실패: {e}")
            return RiskCheckResult(reason="드로우다운 체크 오류")
    
    async def _reset_time_counters(self):
        """시간 기반 카운터 리셋"""
        now = datetime.now(timezone.utc)
        
        # 시간별 리셋
        if (now - self.last_hour_reset).total_seconds() >= 3600:  # 1시간
            self.trade_count_hour = 0
            self.last_hour_reset = now
        
        # 일별 리셋
        if now.date() != self.last_day_reset.date():
            self.trade_count_day = 0
            self.daily_pnl = Decimal('0')
            self.last_day_reset = now
    
    def record_trade(self, profit: Decimal):
        """거래 기록"""
        self.trade_count_hour += 1
        self.trade_count_day += 1
        self.daily_pnl += profit
        self.last_trade_time = datetime.now(timezone.utc)
    
    def _log_risk_event(self, severity: str, message: str):
        """리스크 이벤트 로깅"""
        event = {
            'timestamp': datetime.now(timezone.utc),
            'severity': severity,
            'message': message
        }
        
        self.risk_events.append(event)
        
        # 최근 100개 이벤트만 유지
        if len(self.risk_events) > 100:
            self.risk_events = self.risk_events[-100:]
        
        # 로그 레벨에 따라 출력
        if severity == "CRITICAL":
            logger.critical(f"RISK CRITICAL: {message}")
        elif severity == "HIGH":
            logger.error(f"RISK HIGH: {message}")
        elif severity == "MEDIUM":
            logger.warning(f"RISK MEDIUM: {message}")
        else:
            logger.info(f"RISK LOW: {message}")
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """리스크 설정 업데이트"""
        self.settings.update(new_settings)
        
        # 설정값 재로드
        self.max_loss_percentage = Decimal(str(self.settings.get('max_loss_percentage', -15.0)))
        self.max_drawdown = Decimal(str(self.settings.get('max_drawdown', -20.0)))
        self.max_position_size = Decimal(str(self.settings.get('max_position_size', 80.0)))
        self.daily_loss_limit = Decimal(str(self.settings.get('daily_loss_limit', -5.0)))
        self.max_trades_per_hour = self.settings.get('max_trades_per_hour', 10)
        self.max_trades_per_day = self.settings.get('max_trades_per_day', 100)
        self.volatility_threshold = Decimal(str(self.settings.get('volatility_threshold', 5.0)))
        
        logger.info("리스크 설정 업데이트 완료")
    
    def get_risk_summary(self) -> Dict:
        """리스크 요약 정보"""
        return {
            'capital': float(self.capital),
            'peak_balance': float(self.peak_balance),
            'daily_pnl': float(self.daily_pnl),
            'current_drawdown': float((self.peak_balance - (self.capital + self.daily_pnl)) / self.peak_balance * 100) if self.peak_balance > 0 else 0,
            'trading_activity': {
                'trades_today': self.trade_count_day,
                'trades_this_hour': self.trade_count_hour,
                'last_trade': self.last_trade_time.isoformat() if self.last_trade_time else None
            },
            'risk_limits': {
                'max_loss_percentage': float(self.max_loss_percentage),
                'max_drawdown': float(self.max_drawdown),
                'max_position_size': float(self.max_position_size),
                'daily_loss_limit': float(self.daily_loss_limit),
                'max_trades_per_hour': self.max_trades_per_hour,
                'max_trades_per_day': self.max_trades_per_day
            },
            'recent_events': self.risk_events[-10:] if self.risk_events else []
        }
    
    def reset_daily_stats(self):
        """일일 통계 리셋 (수동)"""
        self.daily_pnl = Decimal('0')
        self.trade_count_day = 0
        self.last_day_reset = datetime.now(timezone.utc)
        logger.info("일일 리스크 통계 리셋")
    
    def emergency_stop_check(self, total_profit: Decimal) -> bool:
        """긴급 중지 조건 체크"""
        # 자본의 50% 이상 손실시 긴급 중지
        emergency_loss_threshold = Decimal('-50.0')
        loss_percentage = (total_profit / self.capital * 100) if self.capital > 0 else Decimal('0')
        
        if loss_percentage <= emergency_loss_threshold:
            self._log_risk_event("CRITICAL", f"긴급 중지: {loss_percentage}% 손실")
            return True
        
        return False


# ===== 팩토리 함수 =====

def create_risk_manager(capital: float, settings: Dict[str, Any]) -> RiskManager:
    """리스크 매니저 팩토리 함수"""
    return RiskManager(capital, settings)


# ===== 테스트 함수 =====

async def test_risk_manager():
    """리스크 매니저 테스트"""
    print("=== 리스크 매니저 테스트 ===")
    
    from decimal import Decimal
    
    # 테스트 설정
    settings = {
        'max_loss_percentage': -10.0,
        'max_drawdown': -15.0,
        'max_position_size': 50.0,
        'daily_loss_limit': -3.0,
        'max_trades_per_hour': 5,
        'max_trades_per_day': 20,
        'volatility_threshold': 3.0
    }
    
    # 리스크 매니저 생성
    risk_manager = RiskManager(1000.0, settings)
    
    # 1. 정상 상황 테스트
    result1 = await risk_manager.check_risk(
        current_price=Decimal('50000'),
        position={'total_cost': 200.0},
        total_profit=Decimal('10.0')
    )
    print(f"정상 상황: {result1.reason}")
    
    # 2. 손실 한계 테스트
    result2 = await risk_manager.check_risk(
        current_price=Decimal('50000'),
        position={'total_cost': 200.0},
        total_profit=Decimal('-120.0')  # 12% 손실
    )
    print(f"손실 한계 테스트: {result2.reason}, 중지 필요: {result2.should_stop}")
    
    # 3. 포지션 크기 테스트
    result3 = await risk_manager.check_risk(
        current_price=Decimal('50000'),
        position={'total_cost': 600.0},  # 60% 포지션
        total_profit=Decimal('10.0')
    )
    print(f"포지션 크기 테스트: {result3.reason}, 포지션 감소 필요: {result3.should_reduce_position}")
    
    # 4. 거래 기록 및 빈도 테스트
    for i in range(6):  # 시간당 한계 초과
        risk_manager.record_trade(Decimal('5.0'))
    
    result4 = await risk_manager.check_risk(
        current_price=Decimal('50000'),
        position={'total_cost': 200.0},
        total_profit=Decimal('10.0')
    )
    print(f"거래 빈도 테스트: {result4.reason}, 일시정지 필요: {result4.should_pause}")
    
    # 5. 리스크 요약
    summary = risk_manager.get_risk_summary()
    print(f"리스크 요약: {summary}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_risk_manager())