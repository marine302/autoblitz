import asyncio
from app.bot_engine.core.bot_runner import BotRunner

async def correct_bot_test():
    print('🤖 올바른 봇 실행 테스트')
    print('=' * 40)
    
    config = {
        'symbol': 'BTC-USDT',
        'capital': 10.0,
        'strategy': 'dantaro_okx_spot_v1',
        'exchange': 'okx',
        'grid_count': 3,
        'grid_gap': 0.1
    }
    
    try:
        bot = BotRunner(1, 1, config)
        await bot.initialize()
        
        print(f'✅ 봇 초기화 성공')
        print(f'✅ 상태: {bot.state}')
        print(f'✅ 심볼: {bot.symbol}')
        print(f'✅ 자본: ${bot.capital}')
        
        # run() 메서드를 별도 태스크로 실행
        print('🚀 봇 실행 시작...')
        bot_task = asyncio.create_task(bot.run())
        
        # 10초 동안 실행
        await asyncio.sleep(10)
        
        # 봇 중지
        print('⏹️ 봇 중지 중...')
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            print('✅ 봇 정상 중지됨')
        
        print('🎉 봇 실행 테스트 성공!')
        
    except Exception as e:
        print(f'❌ 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(correct_bot_test())
