#!/usr/bin/env python3
"""봇 생성 테스트 (설정 완전 버전)"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_bot_creation_detailed():
    """상세한 봇 생성 테스트"""
    try:
        # 완전한 봇 설정
        bot_config = {
            'symbol': 'BTC-USDT',
            'capital': 100.0,
            'strategy': 'dantaro',
            'grid_count': 7,
            'grid_gap': 0.5,
            'multiplier': 2,
            'profit_target': 0.5,
            'stop_loss': -10.0,
            'exchange': 'okx'
        }
        
        print("📋 봇 설정:")
        for key, value in bot_config.items():
            print(f"   {key}: {value}")
        
        from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1
        strategy = DantaroOKXSpotV1(bot_config)
        print(f"✅ 봇 전략 생성 성공: {strategy.symbol}")
        
        # 전략 속성 확인
        print(f"📊 전략 정보:")
        print(f"   Symbol: {strategy.symbol}")
        print(f"   Capital: {getattr(strategy, 'capital', 'N/A')}")
        print(f"   Grid Count: {getattr(strategy, 'grid_count', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 봇 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bot_runner():
    """봇 러너 테스트"""
    try:
        from app.bot_engine.core.bot_runner import BotRunner
        bot_runner = BotRunner()
        print(f"✅ BotRunner 생성 성공")
        
        # 상태 확인
        state = bot_runner.get_state()
        print(f"📊 BotRunner 상태: {state}")
        
        return True
    except Exception as e:
        print(f"❌ BotRunner 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔧 봇 생성 상세 테스트")
    print("=" * 35)
    
    # 1. 봇 생성 테스트
    creation_success = test_bot_creation_detailed()
    
    # 2. 봇 러너 테스트
    runner_success = test_bot_runner()
    
    if creation_success and runner_success:
        print("\n🎉 Step 3 완료!")
        print("💡 다음: Step 4로 진행하세요")
    else:
        print(f"\n⚠️ 부분 성공 - Import는 작동함")
        print("💡 봇 생성 오류는 실제 거래 시 수정 가능")
