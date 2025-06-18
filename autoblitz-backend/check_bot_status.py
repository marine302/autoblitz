import asyncio
from app.bot_engine.core.bot_runner import BotRunner
from datetime import datetime

async def check_bot_activity():
    """봇 활동 상태 확인"""
    config = {
        'symbol': 'BTC-USDT',
        'capital': 20.0,
        'strategy': 'dantaro_okx_spot_v1',
        'exchange': 'okx',
        'grid_count': 3,
        'grid_gap': 0.1
    }
    
    bot = BotRunner(1, 1, config)
    await bot.initialize()
    
    print(f'🤖 봇 상태 확인')
    print(f'상태: {bot.state}')
    print(f'전략: {bot.strategy_name}')
    
    # 30초간 봇 활동 모니터링
    print('\n📊 30초간 봇 활동 모니터링...')
    
    start_time = datetime.now()
    bot_task = asyncio.create_task(bot.run())
    
    for i in range(6):  # 5초마다 상태 체크, 총 30초
        await asyncio.sleep(5)
        current_time = datetime.now()
        elapsed = (current_time - start_time).seconds
        print(f'[{elapsed:02d}초] 봇 실행 중... 상태: {bot.state}')
        
        # 거래 활동 확인
        if hasattr(bot, 'order_count'):
            print(f'  주문 수: {bot.order_count}')
    
    # 봇 중지
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    
    print('\n✅ 모니터링 완료')

asyncio.run(check_bot_activity())
