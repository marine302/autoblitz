#!/usr/bin/env python3
"""
오토블리츠 실전 봇 실행 테스트
파일 경로: /workspaces/autoblitz/autoblitz-backend/live_bot_test.py
"""

import asyncio
import signal
import sys
from datetime import datetime
from app.bot_engine.core.bot_runner import BotRunner
from app.exchanges.okx.client import create_okx_client

class LiveBotTest:
    def __init__(self):
        self.bot = None
        self.running = True
        
    async def run_live_bot(self):
        """실전 봇 실행"""
        print('🤖 오토블리츠 실전 봇 테스트')
        print('=' * 50)
        print(f'⏰ 시작 시간: {datetime.now()}')
        print('=' * 50)
        
        # 봇 설정 (소액 테스트)
        config = {
            'symbol': 'BTC-USDT',
            'capital': 20.0,  # $20 소액 테스트
            'strategy': 'dantaro_okx_spot_v1',
            'exchange': 'okx',
            'grid_count': 3,  # 테스트용 적은 그리드
            'grid_gap': 0.1,  # 0.1% 간격
            'multiplier': 1.5,
            'profit_target': 0.3,
            'stop_loss': -5.0
        }
        
        try:
            # 거래소 연결 테스트
            print('📡 거래소 연결 중...')
            client = await create_okx_client(sandbox=False)
            
            # 현재 시세 확인
            ticker = await client.get_ticker('BTC-USDT')
            print(f'💎 BTC 현재가: ${ticker["last"]:,.2f}')
            
            # 잔고 확인
            balance = await client.get_balance()
            print('💰 계좌 잔고:')
            for currency, data in balance.items():
                if data.get('available', 0) > 0:
                    print(f'   {currency}: {data["available"]}')
            
            await client.close()
            
            # 봇 생성 및 초기화
            print('\n🤖 봇 생성 중...')
            self.bot = BotRunner(1, 1, config)
            await self.bot.initialize()
            
            print(f'✅ 봇 초기화 완료')
            print(f'📊 전략: {self.bot.strategy_name}')
            print(f'💵 자본금: ${self.bot.capital}')
            print(f'📈 심볼: {self.bot.symbol}')
            
            # 봇 실행
            print('\n🚀 봇 실행 시작...')
            print('💡 Ctrl+C를 눌러 중지할 수 있습니다.')
            print('-' * 50)
            
            # run() 메서드 실행
            await self.bot.run()
            
        except KeyboardInterrupt:
            print('\n⏹️ 사용자가 봇을 중지했습니다.')
        except Exception as e:
            print(f'\n❌ 오류 발생: {e}')
            import traceback
            traceback.print_exc()
        finally:
            print('\n🧹 정리 작업 중...')
            if self.bot:
                try:
                    if hasattr(self.bot, 'stop'):
                        await self.bot.stop()
                    elif hasattr(self.bot, '_final_cleanup'):
                        await self.bot._final_cleanup()
                except:
                    pass
            print('✅ 봇 종료 완료')
            print(f'⏰ 종료 시간: {datetime.now()}')

    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print('\n⚠️ 종료 신호 감지...')
        self.running = False
        sys.exit(0)

async def main():
    """메인 함수"""
    test = LiveBotTest()
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, test.signal_handler)
    signal.signal(signal.SIGTERM, test.signal_handler)
    
    # 봇 실행
    await test.run_live_bot()

if __name__ == "__main__":
    # 이벤트 루프 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 프로그램을 종료합니다.')