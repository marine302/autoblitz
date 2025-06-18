#!/usr/bin/env python3
"""실전 봇 완성 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_working_bot():
    """작동하는 봇 생성"""
    try:
        # 완전한 설정
        bot_config = {
            'symbol': 'BTC-USDT',
            'capital': 100.0,
            'initial_amount': 100.0,
            'grid_count': 7,
            'grid_gap': 0.5,
            'multiplier': 2,
            'profit_target': 0.5,
            'stop_loss': -10.0,
            'exchange': 'okx',
            'base_amount': 14.28,  # 계산된 기본 금액
            'min_amount': 5.0      # 최소 주문 금액
        }
        
        print("🤖 실전 봇 생성 테스트")
        print("=" * 30)
        
        from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1
        strategy = DantaroOKXSpotV1(bot_config)
        
        print(f"✅ 봇 생성 성공!")
        print(f"📊 봇 정보:")
        print(f"   Symbol: {strategy.symbol}")
        print(f"   Capital: ${bot_config['capital']}")
        print(f"   Grid Count: {bot_config['grid_count']}")
        
        return True, strategy
        
    except Exception as e:
        print(f"❌ 봇 생성 실패: {e}")
        return False, None

if __name__ == "__main__":
    success, bot = create_working_bot()
    
    if success:
        print("\n🎉 실전 봇 시스템 준비 완료!")
        print("💡 다음 단계:")
        print("1. OKX API 키 설정 (.env 파일)")
        print("2. 소액 실거래 테스트")
        print("3. 웹 인터페이스 구축")
    else:
        print("\n❌ 봇 설정 수정 필요")
