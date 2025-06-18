"""
AutoBlitz 전역 설정 관리
환경 변수 및 상수 정의
"""

import os
from functools import lru_cache
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # 기본 설정
    APP_NAME: str = "AutoBlitz"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API 설정
    API_V1_PREFIX: str = "/api/v1"

    # 데이터베이스 설정
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./autoblitz.db")

    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis 설정 (옵션)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # OKX API 설정
    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "")
    OKX_SECRET_KEY: str = os.getenv("OKX_SECRET_KEY", "")
    OKX_PASSPHRASE: str = os.getenv("OKX_PASSPHRASE", "")
    OKX_SANDBOX: bool = os.getenv("OKX_SANDBOX", "true").lower() == "true"
    OKX_API_URL: str = os.getenv("OKX_API_URL", "https://www.okx.com")
    OKX_SANDBOX_URL: str = os.getenv("OKX_SANDBOX_URL", "https://www.okx.com")

    # 업비트 API 설정
    UPBIT_API_URL: str = os.getenv("UPBIT_API_URL", "https://api.upbit.com")

    # 거래 설정
    DEFAULT_PROFIT_TARGET: float = 0.5  # 0.5%
    DEFAULT_STOP_LOSS: float = -10.0   # -10%
    DEFAULT_ORDER_COUNT: int = 7
    DEFAULT_MULTIPLIER: int = 2

    # 실거래 관련 설정 추가
    LIVE_TRADING_MODE: bool = False  # 실거래 모드 (기본값: False)
    TRADING_ENVIRONMENT: str = "sandbox"  # 거래 환경 (sandbox/production)

    class Config:
        env_file = ".env"
        extra = "allow"  # 추가 환경변수 허용
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()

# 요금제별 봇 제한
PLAN_LIMITS = {
    "lite": {"max_bots": 5, "price_krw": 99000},
    "standard": {"max_bots": 10, "price_krw": 199000},
    "pro": {"max_bots": 20, "price_krw": 299000},
    "enterprise": {"max_bots": 30, "price_krw": 590000}
}

# 거래소별 최소 주문 금액
MIN_ORDER_AMOUNTS = {
    "okx": {
        "spot": 10.0,      # USDT
        "futures": 10.0    # USDT
    },
    "upbit": {
        "spot": 5500.0     # KRW
    }
}

# 상수 정의


class BotStatus:
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TradingType:
    SPOT = "spot"
    FUTURES = "futures"


class OrderSide:
    BUY = "buy"
    SELL = "sell"


class ExchangeType:
    OKX = "okx"
    UPBIT = "upbit"
