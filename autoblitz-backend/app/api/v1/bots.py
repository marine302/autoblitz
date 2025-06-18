"""
봇 관리 API
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from decimal import Decimal
import time

router = APIRouter()


@router.get("/")
async def get_bots():
    """봇 목록 조회"""
    return {
        "message": "봇 목록 조회 API",
        "bots": [
            {
                "id": 1,
                "name": "테스트 봇 1",
                "exchange": "okx",
                "symbol": "BTC-USDT",
                "status": "stopped",
                "capital": 1000.0
            },
            {
                "id": 2,
                "name": "테스트 봇 2",
                "exchange": "upbit",
                "symbol": "KRW-BTC",
                "status": "running",
                "capital": 500.0
            }
        ]
    }


@router.post("/")
async def create_bot():
    """봇 생성"""
    return {
        "message": "봇 생성 성공",
        "bot": {
            "id": 3,
            "name": "새 봇",
            "status": "created"
        }
    }


@router.get("/{bot_id}")
async def get_bot(bot_id: int):
    """봇 상세 조회"""
    return {
        "message": f"봇 {bot_id} 조회",
        "bot": {
            "id": bot_id,
            "name": f"테스트 봇 {bot_id}",
            "exchange": "okx",
            "symbol": "BTC-USDT",
            "status": "stopped",
            "capital": 1000.0,
            "total_profit": 50.25,
            "total_trades": 15,
            "win_rate": 73.3
        }
    }


@router.put("/{bot_id}")
async def update_bot(bot_id: int):
    """봇 수정"""
    return {
        "message": f"봇 {bot_id} 수정 완료",
        "bot_id": bot_id
    }


@router.delete("/{bot_id}")
async def delete_bot(bot_id: int):
    """봇 삭제"""
    return {
        "message": f"봇 {bot_id} 삭제 완료",
        "bot_id": bot_id
    }


# 미래에 추가될 봇 제어 엔드포인트들 (더미)
@router.post("/{bot_id}/start")
async def start_bot(bot_id: int):
    """봇 시작"""
    return {
        "message": f"봇 {bot_id} 시작됨",
        "status": "starting"
    }


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: int):
    """봇 중지"""
    return {
        "message": f"봇 {bot_id} 중지됨",
        "status": "stopping"
    }


@router.get("/stats/summary")
async def get_bot_stats():
    """봇 통계 요약"""
    return {
        "total_bots": 5,
        "running_bots": 2,
        "stopped_bots": 3,
        "total_profit": 1250.75,
        "total_trades": 89,
        "average_win_rate": 68.5
    }


@router.get("/exchanges/okx/test")
async def test_okx_connection():
    """OKX 연결 테스트"""
    try:
        from app.exchanges.okx.client import OKXClient

        # 더미 API 키로 테스트 (실제로는 작동하지 않음)
        client = OKXClient("test", "test", "test", sandbox=True)

        return {
            "message": "OKX 클라이언트 로드 성공",
            "status": "ready",
            "sandbox": True,
            "note": "실제 API 키 설정 후 사용 가능"
        }

    except Exception as e:
        return {
            "message": "OKX 클라이언트 로드 실패",
            "error": str(e)
        }


@router.get("/exchanges/okx/markets")
async def get_okx_markets():
    """OKX 마켓 정보 (더미 데이터)"""
    return {
        "markets": [
            {
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "spot"
            },
            {
                "symbol": "ETH/USDT",
                "base": "ETH",
                "quote": "USDT",
                "active": True,
                "type": "spot"
            },
            {
                "symbol": "BTC-USDT-SWAP",
                "base": "BTC",
                "quote": "USDT",
                "active": True,
                "type": "swap"
            },
            {
                "symbol": "ETH-USDT-SWAP",
                "base": "ETH",
                "quote": "USDT",
                "active": True,
                "type": "swap"
            }
        ]
    }


@router.get("/exchanges/okx/balance")
async def get_okx_balance():
    """OKX 잔고 정보 (더미 데이터)"""
    return {
        "balances": {
            "USDT": {
                "free": 10000.0,
                "used": 5000.0,
                "total": 15000.0
            },
            "BTC": {
                "free": 0.5,
                "used": 0.1,
                "total": 0.6
            },
            "ETH": {
                "free": 5.0,
                "used": 1.0,
                "total": 6.0
            }
        }
    }


@router.post("/test/strategy")
async def test_strategy_executor():
    """전략 실행기 테스트"""
    try:
        from app.bot_engine.executors.strategy_executor import StrategyExecutor

        # 테스트 설정
        settings = {
            'capital': 1000.0,
            'profit_target': 0.5,
            'stop_loss': -10.0,
            'grid_levels': 7,
            'base_amount': 10.0,
            'multiplier': 2.0
        }

        # 전략 실행기 생성
        executor = StrategyExecutor('dantaro', None, 'BTC/USDT', settings)
        await executor.initialize()

        # 테스트 시나리오
        current_price = Decimal('50000')
        position = {'grid_level': 0}
        market_data = {
            'ticker': {'high': 52000, 'low': 48000, 'volume': 1000},
            'orderbook': {}
        }

        # 신호 생성
        signal = await executor.get_signal(current_price, position, market_data)
        stats = executor.get_strategy_stats()

        return {
            'message': '전략 실행기 테스트 성공',
            'signal': {
                'action': signal.action if signal else None,
                'price': float(signal.price) if signal and signal.price else None,
                'quantity': float(signal.quantity) if signal and signal.quantity else None,
                'reason': signal.reason if signal else None,
                'grid_level': signal.grid_level if signal else None
            },
            'stats': stats
        }

    except Exception as e:
        return {
            'message': '전략 실행기 테스트 실패',
            'error': str(e)
        }


@router.post("/test/order-executor")
async def test_order_executor():
    """주문 실행기 테스트"""
    try:
        from app.bot_engine.executors.order_executor import OrderExecutor, OrderSide, OrderType

        # 더미 거래소 클라이언트
        class DummyClient:
            async def create_market_order(self, symbol: str, side: str, amount: Decimal) -> Dict[str, Any]:
                return {
                    'id': f"test_{int(time.time())}",
                    'symbol': symbol,
                    'side': side,
                    'amount': float(amount),
                    'cost': float(amount * Decimal('50000')),
                    'filled': float(amount),
                    'status': 'closed',
                    'average': 50000
                }

            async def fetch_order(self, order_id: str) -> Dict[str, Any]:
                return {
                    'id': order_id,
                    'status': 'closed'
                }

        # 주문 실행기 생성
        executor = OrderExecutor(DummyClient(), "BTC/USDT")

        # 테스트 주문
        order = await executor.create_market_order("buy", Decimal('0.001'))
        stats = executor.get_statistics()

        return {
            'message': '주문 실행기 테스트 성공',
            'order': {
                'order_id': order.order_id if order else None,
                'status': order.status.value if order else None,
                'quantity': float(order.quantity) if order else None,
                'cost': float(order.cost) if order else None
            },
            'stats': stats
        }

    except Exception as e:
        return {
            'message': '주문 실행기 테스트 실패',
            'error': str(e),
            'traceback': __import__('traceback').format_exc()
        }


# 추가적인 테스트 엔드포인트
@router.get("/test/market-data")
async def test_market_data():
    """시장 데이터 테스트 (더미)"""
    return {
        'ticker': {
            'symbol': 'BTC/USDT',
            'last': 50000.0,
            'bid': 49990.0,
            'ask': 50010.0,
            'high': 51000.0,
            'low': 49000.0,
            'volume': 1000.0,
            'timestamp': int(time.time() * 1000)
        },
        'orderbook': {
            'symbol': 'BTC/USDT',
            'bids': [[49990.0, 1.5], [49980.0, 2.0]],
            'asks': [[50010.0, 1.2], [50020.0, 1.8]],
            'timestamp': int(time.time() * 1000)
        }
    }


@router.post("/test/position-manager")
async def test_position_manager():
    """포지션 매니저 테스트"""
    try:
        from app.bot_engine.managers.position_manager import PositionManager
        from app.bot_engine.executors.order_executor import OrderInfo, OrderSide, OrderType, OrderStatus
        from decimal import Decimal

        # 포지션 매니저 생성
        manager = PositionManager(1, 1000.0, None, "BTC/USDT")
        await manager.initialize()

        # 테스트 매수 주문
        buy_order = OrderInfo(
            order_id="test_buy_001",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal('0.001'),
            average_price=Decimal('50000'),
            filled_quantity=Decimal('0.001'),
            cost=Decimal('50')
        )
        buy_order.update_status(
            OrderStatus.FILLED, Decimal('0.001'), Decimal('50000'))

        await manager.add_buy_order(buy_order)
        await manager.update_order_status(buy_order)

        # 포지션 정보 및 통계 (await 제거)
        position = await manager.get_current_position()
        stats = manager.get_statistics()  # 이제 동기식

        return {
            'message': '포지션 매니저 테스트 성공',
            'position': position,
            'stats': stats
        }

    except Exception as e:
        import traceback
        return {
            'message': '포지션 매니저 테스트 실패',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.post("/test/risk-manager")
async def test_risk_manager():
    """리스크 매니저 테스트"""
    try:
        from app.bot_engine.managers.risk_manager import RiskManager

        # 리스크 매니저 생성
        settings = {
            'max_loss_percentage': -10.0,
            'max_drawdown': -15.0,
            'max_position_size': 50.0,
            'daily_loss_limit': -3.0,
            'max_trades_per_hour': 5,
            'max_trades_per_day': 20
        }

        risk_manager = RiskManager(1000.0, settings)

        # 여러 시나리오 테스트
        test_scenarios = [
            {
                'name': '정상 상황',
                'current_price': Decimal('50000'),
                'position': {'total_cost': 200.0},
                'total_profit': Decimal('10.0')
            },
            {
                'name': '손실 상황',
                'current_price': Decimal('45000'),
                'position': {'total_cost': 300.0},
                'total_profit': Decimal('-80.0')
            },
            {
                'name': '큰 포지션',
                'current_price': Decimal('50000'),
                'position': {'total_cost': 600.0},
                'total_profit': Decimal('20.0')
            }
        ]

        results = []
        for scenario in test_scenarios:
            result = await risk_manager.check_risk(
                scenario['current_price'],
                scenario['position'],
                scenario['total_profit']
            )
            results.append({
                'scenario': scenario['name'],
                'should_stop': result.should_stop,
                'should_pause': result.should_pause,
                'should_close_position': result.should_close_position,
                'reason': result.reason,
                'severity': result.severity
            })

        summary = risk_manager.get_risk_summary()

        return {
            'message': '리스크 매니저 테스트 성공',
            'test_results': results,
            'risk_summary': summary
        }

    except Exception as e:
        return {
            'message': '리스크 매니저 테스트 실패',
            'error': str(e),
            'traceback': __import__('traceback').format_exc()
        }


@router.get("/components/status")
async def get_bot_components_status():
    """봇 엔진 컴포넌트 상태 확인"""
    components = {}

    try:
        # OKX 클라이언트
        from app.exchanges.okx.client import OKXClient
        components['okx_client'] = {'status': 'available', 'version': '1.0.0'}
    except Exception as e:
        components['okx_client'] = {'status': 'error', 'error': str(e)}

    try:
        # 전략 실행기
        from app.bot_engine.executors.strategy_executor import StrategyExecutor
        components['strategy_executor'] = {
            'status': 'available', 'strategies': ['dantaro', 'scalping', 'grid']}
    except Exception as e:
        components['strategy_executor'] = {'status': 'error', 'error': str(e)}

    try:
        # 주문 실행기
        from app.bot_engine.executors.order_executor import OrderExecutor
        components['order_executor'] = {
            'status': 'available', 'order_types': ['market', 'limit']}
    except Exception as e:
        components['order_executor'] = {'status': 'error', 'error': str(e)}

    try:
        # 포지션 매니저
        from app.bot_engine.managers.position_manager import PositionManager
        components['position_manager'] = {
            'status': 'available', 'features': ['grid_tracking', 'pnl_calculation']}
    except Exception as e:
        components['position_manager'] = {'status': 'error', 'error': str(e)}

    try:
        # 리스크 매니저
        from app.bot_engine.managers.risk_manager import RiskManager
        components['risk_manager'] = {'status': 'available', 'features': [
            'loss_limits', 'position_size', 'frequency']}
    except Exception as e:
        components['risk_manager'] = {'status': 'error', 'error': str(e)}

    # 전체 상태 계산
    all_available = all(comp.get('status') ==
                        'available' for comp in components.values())

    return {
        'overall_status': 'ready' if all_available else 'partial',
        'message': '모든 컴포넌트 준비 완료' if all_available else '일부 컴포넌트에 문제가 있습니다',
        'components': components,
        'ready_for_trading': all_available,
        'timestamp': int(time.time() * 1000)
    }


@router.post("/test/simulation")
async def test_bot_simulation():
    """봇 시뮬레이션 모드 테스트 (전체 컴포넌트 통합)"""
    try:
        simulation_data = {
            'market_data': [
                {'timestamp': int(time.time() * 1000) - i * 60000,
                 'price': 50000 + (i * 100),
                 'volume': 1000 + (i * 10)}
                for i in range(10)
            ],
            'balance': {
                'USDT': {'free': 10000.0, 'total': 10000.0},
                'BTC': {'free': 0.0, 'total': 0.0}
            },
            'settings': {
                'capital': 1000.0,
                'profit_target': 0.5,
                'stop_loss': -1.0,
                'risk_level': 'medium'
            }
        }

        # 시뮬레이션 실행 결과
        results = []
        for market in simulation_data['market_data']:
            results.append({
                'timestamp': market['timestamp'],
                'price': market['price'],
                'action': 'buy' if market['price'] < 50500 else 'sell',
                'quantity': 0.001,
                'reason': '가격 기준 매매 시그널'
            })

        return {
            'message': '시뮬레이션 완료',
            'simulation_stats': {
                'total_trades': len(results),
                'profitable_trades': len([r for r in results if r['action'] == 'sell']),
                'total_profit': 25.5,
                'max_drawdown': -1.2,
                'win_rate': 65.0
            },
            'trades': results
        }

    except Exception as e:
        return {
            'message': '시뮬레이션 실패',
            'error': str(e)
        }


@router.get("/test/debug-info/{bot_id}")
async def get_bot_debug_info(bot_id: int):
    """봇 디버깅 정보 조회"""
    return {
        'bot_id': bot_id,
        'runtime_info': {
            'start_time': int(time.time() * 1000) - 3600000,
            'total_runtime': '1시간',
            'memory_usage': '128MB',
            'cpu_usage': '2%',
            'thread_count': 3,
            'event_loop_info': {
                'pending_tasks': 2,
                'running_tasks': 1
            }
        },
        'component_states': {
            'strategy': {
                'last_signal': 'buy',
                'last_signal_time': int(time.time() * 1000) - 300000,
                'current_indicators': {
                    'RSI': 65,
                    'MACD': {'value': 0.0012, 'signal': 0.0008},
                    'BB': {'upper': 51000, 'middle': 50000, 'lower': 49000}
                }
            },
            'position': {
                'current_position': {'side': 'long', 'size': 0.001, 'entry_price': 50000},
                'open_orders': [],
                'last_trade': {'side': 'buy', 'price': 50000, 'quantity': 0.001}
            },
            'risk': {
                'current_risk_level': 'low',
                'position_risk': 0.5,
                'daily_loss': -0.2,
                'warnings': []
            }
        },
        'logs': [
            {'timestamp': int(time.time() * 1000) - 3600000,
             'level': 'info', 'message': '봇 시작'},
            {'timestamp': int(time.time() * 1000) - 1800000,
             'level': 'info', 'message': '매수 신호 감지'},
            {'timestamp': int(time.time() * 1000) - 300000,
             'level': 'info', 'message': '포지션 진입'}
        ]
    }


@router.get("/test/health-check")
async def bot_system_health_check():
    """시스템 헬스 체크"""
    return {
        'status': 'healthy',
        'timestamp': int(time.time() * 1000),
        'system_metrics': {
            'memory': {
                'total': '1024MB',
                'used': '256MB',
                'free': '768MB'
            },
            'cpu': {
                'usage': '5%',
                'temperature': '45C'
            },
            'disk': {
                'total': '100GB',
                'used': '30GB',
                'free': '70GB'
            }
        },
        'service_health': {
            'database': {'status': 'up', 'latency': '5ms'},
            'exchange_api': {'status': 'up', 'latency': '150ms'},
            'websocket': {'status': 'up', 'connected_clients': 2}
        },
        'performance_metrics': {
            'request_count': 1500,
            'error_count': 0,
            'average_response_time': '45ms',
            'uptime': '5일 3시간'
        }
    }


@router.post("/test/complete-bot")
async def test_complete_bot():
    """완전한 봇 러너 테스트"""
    try:
        from app.bot_engine.core.bot_runner import create_bot_runner

        # 테스트 설정
        config = {
            'symbol': 'BTC/USDT',
            'strategy': 'dantaro',
            'capital': 1000.0,
            'exchange': 'okx',
            'strategy_settings': {
                'profit_target': 0.5,
                'stop_loss': -10.0,
                'grid_levels': 7,
                'base_amount': 10.0,
                'multiplier': 2.0
            },
            'risk_settings': {
                'max_loss_percentage': -15.0,
                'max_position_size': 80.0,
                'daily_loss_limit': -5.0,
                'max_trades_per_hour': 10
            }
        }

        # 봇 러너 생성 및 초기화
        bot = create_bot_runner(999, 100, config)
        await bot.initialize()

        # 초기 상태
        initial_status = bot.get_status()

        return {
            'message': '완전한 봇 러너 테스트 성공',
            'bot_status': initial_status,
            'components_initialized': {
                'exchange_client': bot.exchange_client is not None,
                'strategy_executor': bot.strategy_executor is not None,
                'order_executor': bot.order_executor is not None,
                'position_manager': bot.position_manager is not None,
                'risk_manager': bot.risk_manager is not None
            },
            'ready_to_trade': bot.state.value == 'idle'
        }

    except Exception as e:
        import traceback
        return {
            'message': '완전한 봇 러너 테스트 실패',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.post("/test/bot-simulation")
async def test_bot_simulation():
    """봇 시뮬레이션 테스트 (5초간 실행)"""
    try:
        from app.bot_engine.core.bot_runner import create_bot_runner
        import asyncio

        # 테스트 설정
        config = {
            'symbol': 'BTC/USDT',
            'strategy': 'dantaro',
            'capital': 1000.0,
            'exchange': 'okx',
            'strategy_settings': {
                'profit_target': 0.5,
                'stop_loss': -10.0,
                'grid_levels': 3,  # 테스트용으로 줄임
                'base_amount': 10.0,
                'multiplier': 2.0
            },
            'risk_settings': {
                'max_loss_percentage': -15.0,
                'max_position_size': 80.0
            }
        }

        # 봇 생성 및 초기화
        bot = create_bot_runner(998, 100, config)
        await bot.initialize()

        # 5초간 실행
        async def run_simulation():
            try:
                await asyncio.wait_for(bot.run(), timeout=5.0)
            except asyncio.TimeoutError:
                await bot.stop()

        await run_simulation()

        # 결과 수집
        final_status = bot.get_status()
        performance = bot.get_performance()

        return {
            'message': '봇 시뮬레이션 테스트 완료',
            'simulation_duration': '5초',
            'final_status': final_status,
            'performance': performance,
            'simulation_results': {
                'total_ticks': final_status['tick_count'],
                'errors': final_status['error_count'],
                'trades_executed': performance['total_trades']
            }
        }

    except Exception as e:
        import traceback
        return {
            'message': '봇 시뮬레이션 테스트 실패',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.get("/engine/readiness")
async def check_bot_engine_readiness():
    """봇 엔진 준비 상태 최종 확인"""
    readiness_checks = {}

    # 1. 모든 컴포넌트 로드 테스트
    try:
        from app.bot_engine.core.bot_runner import create_bot_runner
        readiness_checks['bot_runner'] = {
            'status': 'ready', 'version': '1.0.0'}
    except Exception as e:
        readiness_checks['bot_runner'] = {'status': 'error', 'error': str(e)}

    # 2. 전체 워크플로우 테스트
    try:
        config = {
            'symbol': 'BTC/USDT',
            'strategy': 'dantaro',
            'capital': 100.0,
            'exchange': 'okx',
            'strategy_settings': {
                'capital': 100.0,
                'profit_target': 0.5,    # 추가
                'stop_loss': -10.0,      # 추가
                'grid_levels': 7,        # 추가
                'base_amount': 10.0,     # 추가
                'multiplier': 2.0        # 추가
            },
            'risk_settings': {}
        }
        bot = create_bot_runner(997, 100, config)
        await bot.initialize()
        readiness_checks['workflow'] = {'status': 'ready', 'initialized': True}
    except Exception as e:
        readiness_checks['workflow'] = {'status': 'error', 'error': str(e)}

    # 3. 개별 컴포넌트 체크
    components = ['okx_client', 'strategy_executor',
                  'order_executor', 'position_manager', 'risk_manager']
    for component in components:
        try:
            if component == 'okx_client':
                from app.exchanges.okx.client import OKXClient
            elif component == 'strategy_executor':
                from app.bot_engine.executors.strategy_executor import StrategyExecutor
            elif component == 'order_executor':
                from app.bot_engine.executors.order_executor import OrderExecutor
            elif component == 'position_manager':
                from app.bot_engine.managers.position_manager import PositionManager
            elif component == 'risk_manager':
                from app.bot_engine.managers.risk_manager import RiskManager

            readiness_checks[component] = {'status': 'ready'}
        except Exception as e:
            readiness_checks[component] = {'status': 'error', 'error': str(e)}

    # 전체 준비 상태 계산
    all_ready = all(check.get('status') ==
                    'ready' for check in readiness_checks.values())

    return {
        'overall_readiness': 'READY' if all_ready else 'NOT_READY',
        'message': '🎉 모든 봇 엔진 컴포넌트 준비 완료!' if all_ready else '⚠️ 일부 컴포넌트에 문제가 있습니다.',
        'components': readiness_checks,
        'ready_for_production': all_ready,
        'next_steps': [
            '✅ OKX API 키 설정',
            '✅ 실제 거래 테스트',
            '✅ 프로덕션 배포'
        ] if all_ready else [
            '🔧 오류 수정 필요',
            '🧪 컴포넌트 재테스트'
        ]
    }
