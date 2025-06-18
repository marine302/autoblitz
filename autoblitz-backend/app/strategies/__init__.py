"""
전략 레지스트리
"""

from typing import Dict, Type
from .base.strategy import BaseStrategy
from .dantaro.okx_spot_v1 import DantaroOKXSpotV1

# 전략 레지스트리
STRATEGIES: Dict[str, Type[BaseStrategy]] = {
    "dantaro_okx_spot_v1": DantaroOKXSpotV1,
}

def get_strategy(strategy_id: str, bot_config: Dict) -> BaseStrategy:
    """전략 인스턴스 생성"""
    strategy_class = STRATEGIES.get(strategy_id)
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_id}")
    
    return strategy_class(bot_config)