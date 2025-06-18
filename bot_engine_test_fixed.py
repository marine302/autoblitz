#!/usr/bin/env python3
"""봇 엔진 테스트 (경로 수정 버전)"""

import sys
import os

# 현재 디렉토리를 Python path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_file_existence():
    """파일 존재 확인"""
    files_to_check = [
        'app/bot_engine/core/bot_runner.py',
        'app/strategies/dantaro/okx_spot_v1.py',
        'app/exchanges/okx/client.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path} 존재")
        else:
            print(f"❌ {file_path} 없음")
            return False
    return True

def test_imports():
    """핵심 모듈 import 테스트"""
    try:
        # 절대 import 방식으로 변경
        import app.bot_engine.core.bot_runner as bot_runner_module
        print("✅ bot_runner 모듈 import 성공")
        
        import app.strategies.dantaro.okx_spot_v1 as strategy_module
        print("✅ strategy 모듈 import 성공")
        
        import app.exchanges.okx.client as okx_module
        print("✅ okx_client 모듈 import 성공")
        
        return True, (bot_runner_module, strategy_module, okx_module)
        
    except Exception as e:
        print(f"❌ Import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_class_creation(modules):
    """클래스 생성 테스트"""
    try:
        bot_runner_module, strategy_module, okx_module = modules
        
        # BotRunner 클래스 테스트
        BotRunner = getattr(bot_runner_module, 'BotRunner', None)
        if BotRunner:
            bot_runner = BotRunner()
            print("✅ BotRunner 클래스 생성 성공")
        else:
            print("❌ BotRunner 클래스 없음")
            return False
        
        # Strategy 클래스 테스트
        DantaroOKXSpotV1 = getattr(strategy_module, 'DantaroOKXSpotV1', None)
        if DantaroOKXSpotV1:
            strategy = DantaroOKXSpotV1({
                'symbol': 'BTC-USDT',
                'capital': 100.0
            })
            print(f"✅ Strategy 클래스 생성 성공: {strategy.symbol}")
        else:
            print("❌ DantaroOKXSpotV1 클래스 없음")
            return False
        
        # OKX Client 클래스 테스트
        OKXClient = getattr(okx_module, 'OKXClient', None)
        if OKXClient:
            okx_client = OKXClient()
            print("✅ OKXClient 클래스 생성 성공")
        else:
            print("❌ OKXClient 클래스 없음")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 클래스 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🤖 봇 엔진 테스트 (수정 버전)")
    print("=" * 40)
    
    # 1. 파일 존재 확인
    if not test_file_existence():
        print("\n❌ 필수 파일이 없습니다")
        exit(1)
    
    # 2. Import 테스트
    import_success, modules = test_imports()
    
    if import_success:
        # 3. 클래스 생성 테스트
        creation_success = test_class_creation(modules)
        
        if creation_success:
            print("\n🎉 모든 테스트 통과!")
            print("💡 다음: Step 4로 진행하세요")
        else:
            print("\n❌ 클래스 생성 실패")
    else:
        print("\n❌ Import 실패")
