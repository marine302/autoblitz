# app/safety/trading_safety.py
import os
import time
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SafetyLimits:
    """안전 한도 설정"""
    max_daily_loss: float = 50.0  # 일일 최대 손실 (USDT)
    max_position_size: float = 100.0  # 최대 포지션 크기 (USDT)
    max_concurrent_bots: int = 5  # 최대 동시 실행 봇 수
    min_account_balance: float = 10.0  # 최소 계좌 잔고 (USDT)
    max_drawdown_percent: float = 20.0  # 최대 낙폭 (%)

class TradingSafetyManager:
    """실거래 안전장치 관리자"""
    
    def __init__(self):
        self.limits = SafetyLimits()
        self.daily_stats = {}
        self.emergency_stop = False
        self.last_reset_date = datetime.now().date()
        
        # 기본값으로 설정 (환경변수 없어도 동작)
        self.limits.max_daily_loss = 50.0
        self.limits.max_position_size = 100.0
        self.limits.max_concurrent_bots = 5
        self.limits.min_account_balance = 10.0
        
        logger.info(f"안전장치 초기화 완료: 일일손실한도=${self.limits.max_daily_loss}, 최대포지션=${self.limits.max_position_size}")
    
    def reset_daily_stats(self):
        """일일 통계 리셋"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            logger.info("일일 통계 리셋")
            self.daily_stats = {
                'total_trades': 0,
                'total_profit_loss': 0.0,
                'max_drawdown': 0.0,
                'active_bots': 0
            }
            self.last_reset_date = current_date
    
    def validate_new_trade(self, symbol: str, side: str, size: float, price: float = None) -> tuple[bool, str]:
        """새 거래 검증"""
        self.reset_daily_stats()
        
        # 긴급 정지 확인
        if self.emergency_stop:
            return False, "긴급 정지 상태입니다."
        
        # 포지션 크기 확인
        if size > self.limits.max_position_size:
            return False, f"포지션 크기 초과: {size} > {self.limits.max_position_size}"
        
        # 일일 손실 한도 확인
        if self.daily_stats.get('total_profit_loss', 0) <= -self.limits.max_daily_loss:
            return False, f"일일 손실 한도 도달: {self.daily_stats['total_profit_loss']}"
        
        # 동시 실행 봇 수 확인
        if self.daily_stats.get('active_bots', 0) >= self.limits.max_concurrent_bots:
            return False, f"최대 동시 봇 수 초과: {self.daily_stats['active_bots']} >= {self.limits.max_concurrent_bots}"
        
        return True, "거래 승인"
    
    def record_trade_result(self, profit_loss: float, bot_id: str = None):
        """거래 결과 기록"""
        self.reset_daily_stats()
        
        self.daily_stats['total_trades'] = self.daily_stats.get('total_trades', 0) + 1
        self.daily_stats['total_profit_loss'] = self.daily_stats.get('total_profit_loss', 0) + profit_loss
        
        # 낙폭 계산
        if profit_loss < 0:
            current_drawdown = abs(profit_loss)
            max_drawdown = self.daily_stats.get('max_drawdown', 0)
            self.daily_stats['max_drawdown'] = max(max_drawdown, current_drawdown)
        
        # 긴급 정지 조건 확인
        self.check_emergency_conditions()
        
        logger.info(f"거래 기록: P&L={profit_loss}, 총 P&L={self.daily_stats['total_profit_loss']}")
    
    def check_emergency_conditions(self):
        """긴급 정지 조건 확인"""
        # 일일 손실 한도 초과
        if self.daily_stats.get('total_profit_loss', 0) <= -self.limits.max_daily_loss:
            self.trigger_emergency_stop(f"일일 손실 한도 초과: {self.daily_stats['total_profit_loss']}")
        
        # 최대 낙폭 초과
        drawdown_percent = (self.daily_stats.get('max_drawdown', 0) / self.limits.max_position_size) * 100
        if drawdown_percent >= self.limits.max_drawdown_percent:
            self.trigger_emergency_stop(f"최대 낙폭 초과: {drawdown_percent}%")
    
    def trigger_emergency_stop(self, reason: str):
        """긴급 정지 발동"""
        if not self.emergency_stop:
            self.emergency_stop = True
            logger.critical(f"🚨 긴급 정지 발동: {reason}")
    
    def reset_emergency_stop(self):
        """긴급 정지 해제 (관리자만)"""
        self.emergency_stop = False
        logger.warning("긴급 정지 해제됨")
    
    def get_safety_status(self) -> Dict:
        """안전장치 상태 조회"""
        self.reset_daily_stats()
        
        return {
            'emergency_stop': self.emergency_stop,
            'daily_stats': self.daily_stats,
            'limits': {
                'max_daily_loss': self.limits.max_daily_loss,
                'max_position_size': self.limits.max_position_size,
                'max_concurrent_bots': self.limits.max_concurrent_bots,
                'min_account_balance': self.limits.min_account_balance
            },
            'remaining_capacity': {
                'daily_loss_remaining': self.limits.max_daily_loss + self.daily_stats.get('total_profit_loss', 0),
                'bots_remaining': self.limits.max_concurrent_bots - self.daily_stats.get('active_bots', 0)
            }
        }

class RealTradingValidator:
    """실거래 검증기"""
    
    def __init__(self, safety_manager: TradingSafetyManager):
        self.safety_manager = safety_manager
    
    def validate_bot_start(self, bot_config: Dict) -> tuple[bool, str]:
        """봇 시작 전 검증"""
        # 안전장치 확인
        can_trade, reason = self.safety_manager.validate_new_trade(
            symbol=bot_config.get('symbol', 'BTC-USDT'),
            side='buy',  # 첫 매수
            size=bot_config.get('initial_amount', 20.0)
        )
        
        if not can_trade:
            return False, f"안전장치 차단: {reason}"
        
        # 봇 설정 검증
        if bot_config.get('capital', 0) < 10:
            return False, "최소 자본금 $10 이상 필요"
        
        if not bot_config.get('symbol'):
            return False, "거래 심볼이 설정되지 않음"
        
        return True, "봇 시작 승인"
    
    def validate_order_execution(self, order_data: Dict) -> tuple[bool, str]:
        """주문 실행 전 검증"""
        # 마지막 안전 확인
        can_trade, reason = self.safety_manager.validate_new_trade(
            symbol=order_data.get('symbol', 'BTC-USDT'),
            side=order_data.get('side', 'buy'),
            size=order_data.get('size', 20.0),
            price=order_data.get('price')
        )
        
        return can_trade, reason

# 전역 안전장치 인스턴스
safety_manager = TradingSafetyManager()
trading_validator = RealTradingValidator(safety_manager)