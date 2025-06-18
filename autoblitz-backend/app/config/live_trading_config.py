# app/config/live_trading_config.py
from typing import Dict, Any
import os
import time

class LiveTradingConfig:
    """실거래 설정"""
    
    # 소액 테스트 설정
    SMALL_TEST_CONFIG = {
        'symbol': 'BTC-USDT',
        'capital': 20.0,  # $20 소액 테스트
        'initial_amount': 20.0,
        'grid_count': 5,  # 그리드 수 줄임 (리스크 감소)
        'grid_gap': 1.0,  # 그리드 간격 넓힘 (안전성 증대)
        'multiplier': 1.5,  # 배수 줄임 (기존 2 → 1.5)
        'profit_target': 1.0,  # 목표 수익률 높임 (0.5% → 1.0%)
        'stop_loss': -5.0,  # 손절선 완화 (-10% → -5%)
        'base_amount': 4.0,  # 계산된 기본 금액
        'min_amount': 4.0,  # 최소 주문 금액
        'max_orders': 5,  # 최대 주문 수
        'strategy': 'dantaro_conservative'  # 보수적 전략
    }
    
    # 안전 설정
    SAFETY_SETTINGS = {
        'max_daily_loss': 10.0,  # 일일 최대 손실 $10
        'max_position_size': 20.0,  # 최대 포지션 $20
        'max_concurrent_bots': 1,  # 동시 실행 봇 1개만
        'min_account_balance': 50.0,  # 최소 잔고 $50
        'emergency_stop_loss': -50.0,  # 긴급 정지 손실액
        'auto_stop_on_loss': True,  # 손실 시 자동 정지
        'trade_confirmation': True,  # 거래 확인 단계 추가
    }
    
    @classmethod
    def get_config_by_level(cls, level: str) -> Dict[str, Any]:
        """레벨별 설정 반환"""
        config = cls.SMALL_TEST_CONFIG.copy()
        config.update({'safety': cls.SAFETY_SETTINGS})
        return config
    
    @classmethod
    def validate_live_environment(cls) -> tuple[bool, str]:
        """실거래 환경 검증"""
        # API 키 확인 (선택사항)
        api_key = os.getenv('OKX_API_KEY')
        if not api_key:
            return True, "데모 모드로 실행됩니다 (API 키 없음)"
        
        # 실거래 모드 확인
        live_mode = os.getenv('LIVE_TRADING_MODE', 'false').lower() == 'true'
        if live_mode:
            return True, "실거래 모드 활성화됨"
        else:
            return True, "데모 모드로 실행됩니다"

# 실거래 테스트 봇 생성 함수
def create_live_test_bot(level: str = 'small') -> Dict[str, Any]:
    """실거래 테스트 봇 생성"""
    # 환경 검증
    is_valid, message = LiveTradingConfig.validate_live_environment()
    if not is_valid:
        raise ValueError(f"환경 검증 실패: {message}")
    
    # 설정 로드
    config = LiveTradingConfig.get_config_by_level(level)
    
    # 추가 메타데이터
    config.update({
        'bot_id': f"live_test_{level}_{int(time.time())}",
        'created_at': time.time(),
        'mode': 'live_trading',
        'test_level': level,
        'auto_stop': True,
        'notifications': True
    })
    
    return config