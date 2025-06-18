#!/usr/bin/env python3
"""간단한 봇 엔진 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """핵심 모듈 import 테스트"""
    try:
        from app.bot_engine.core.bot_runner import BotRunner
        print("✅ BotRunner import 성공")
        
        from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1
        print("✅ DantaroOKXSpotV1 import 성공")
        
        from app.exchanges.okx.client import OKXClient
        print("✅ OKXClient import 성공")
        
        return True
    except Exception as e:
        print(f"❌ Import 실패: {e}")
        return False

def test_bot_creation():
    """봇 생성 테스트"""
    try:
        bot_config = {
            'symbol': 'BTC-USDT',
            'capital': 100.0,
            'strategy': 'dantaro'
        }
        
        from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1
        strategy = DantaroOKXSpotV1(bot_config)
        print(f"✅ 봇 전략 생성 성공: {strategy.symbol}")
        
        return True
    except Exception as e:
        print(f"❌ 봇 생성 실패: {e}")
        return False

if __name__ == "__main__":
    print("🤖 봇 엔진 개별 테스트")
    print("=" * 30)
    
    # 1. Import 테스트
    import_success = test_imports()
    
    # 2. 봇 생성 테스트
    if import_success:
        creation_success = test_bot_creation()
        
        if creation_success:
            print("\n🎉 모든 테스트 통과!")
            print("💡 다음: Step 4로 진행하세요")
        else:
            print("\n❌ 봇 생성 실패")
    else:
        print("\n❌ Import 실패")
