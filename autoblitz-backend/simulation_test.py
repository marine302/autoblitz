import asyncio
from app.bot_engine.core.bot_runner import BotRunner
from app.exchanges.okx.client import create_okx_client

async def simulation_test():
    print('🎮 거래 시뮬레이션 테스트')
    print('=' * 40)
    
    # 봇 설정
    config = {
        'symbol': 'BTC-USDT',
        'capital': 100.0,  # 시뮬레이션용 자본
        'strategy': 'dantaro_okx_spot_v1',
        'exchange': 'okx',
        'grid_count': 7,
        'grid_gap': 0.5,
        'multiplier': 2,
        'profit_target': 0.5,
        'stop_loss': -10.0
    }
    
    try:
        # 거래소 클라이언트 테스트
        client = await create_okx_client(sandbox=False)
        ticker = await client.get_ticker('BTC-USDT')
        print(f'💎 현재 BTC 가격: ${ticker["last"]:,.2f}')
        
        balance = await client.get_balance()
        print(f'💰 계좌 잔고: {list(balance.keys())}')
        
        # 봇 생성 및 초기화
        bot = BotRunner(1, 1, config)
        await bot.initialize()
        
        print(f'✅ 봇 생성 완료')
        print(f'📊 전략: {bot.strategy_name}')
        print(f'💵 자본금: ${bot.capital}')
        print(f'📈 심볼: {bot.symbol}')
        
        # 전략 정보 출력
        if hasattr(bot, 'strategy_executor') and bot.strategy_executor:
            if hasattr(bot.strategy_executor, 'strategy'):
                strategy = bot.strategy_executor.strategy
                info = strategy.get_strategy_info()
                print(f'🎯 그리드 수: {info["grid_count"]}')
                print(f'📏 그리드 간격: {info["grid_gap"]}%')
                print(f'💰 필요 자본: ${info["total_required_capital"]:,.2f}')
        
        await client.close()
        print('🎉 시뮬레이션 테스트 성공!')
        
    except Exception as e:
        print(f'❌ 실패: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simulation_test())
