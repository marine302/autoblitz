import asyncio
from app.bot_engine.core.bot_runner import BotRunner

async def minimal_test():
    print('🔧 최소 봇 테스트')
    config = {
        'symbol': 'BTC-USDT',
        'capital': 10.0,
        'strategy': 'dantaro_okx_spot_v1',
        'exchange': 'okx'
    }
    
    bot = BotRunner(1, 1, config)
    await bot.initialize()
    print(f'✅ 봇 초기화 성공: {bot.state}')
    
    # 봇이 run() 메서드를 가지고 있는지 확인
    if hasattr(bot, 'run'):
        print('✅ run() 메서드 존재')
        # 5초간만 실행
        task = asyncio.create_task(bot.run())
        await asyncio.sleep(5)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        print('✅ 5초 실행 완료')
    else:
        print('❌ run() 메서드 없음')
        print('사용 가능한 메서드:', [m for m in dir(bot) if not m.startswith('_')])

if __name__ == "__main__":
    asyncio.run(minimal_test())
