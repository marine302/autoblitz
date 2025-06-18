# structure_based_trading_bot.py
# 정확한 기존 모듈 구조 분석 기반 실거래 봇

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('real_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StructureBasedTradingManager:
    """기존 모듈 구조에 정확히 맞춘 실거래 관리자"""

    def __init__(self):
        self.settings = None
        self.okx_client = None
        self.active_bots = {}
        self.user_id = 1  # 테스트 사용자 ID
        self.next_bot_id = 1

    async def initialize(self):
        """시스템 초기화"""
        try:
            logger.info("🚀 구조 기반 실거래 시스템 초기화")

            # 1. 설정 로드
            await self.load_settings()

            # 2. OKX 클라이언트 초기화
            await self.initialize_okx_client()

            # 3. 시스템 상태 확인
            await self.check_system_status()

            logger.info("🎯 시스템 초기화 완료!")

        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            raise

    async def load_settings(self):
        """설정 로드"""
        try:
            from app.core.config import settings
            self.settings = settings

            logger.info("✅ 설정 로드 완료")

            # API 키 상태 확인
            api_key = getattr(settings, 'OKX_API_KEY', None)
            secret_key = getattr(settings, 'OKX_SECRET_KEY', None)
            passphrase = getattr(settings, 'OKX_PASSPHRASE', None)

            if api_key and secret_key and passphrase:
                logger.info("🔑 OKX API 키 설정 확인됨")
                self.api_credentials = {
                    'api_key': api_key,
                    'secret_key': secret_key,
                    'passphrase': passphrase
                }
            else:
                logger.warning("⚠️ OKX API 키가 설정되지 않음 - 데모 모드로 진행")
                self.api_credentials = None

        except Exception as e:
            logger.error(f"❌ 설정 로드 실패: {e}")
            raise

    async def initialize_okx_client(self):
        """OKX 클라이언트 초기화 (오류 처리 강화)"""
        try:
            logger.info("🔍 시스템 상태 확인 중...")

            # 공개 API로 시세 조회 테스트
            await self.test_public_api()

            # API 키가 있고 클라이언트가 정상이면 인증 API 테스트
            if self.okx_client and self.api_credentials:
                await self.test_private_api()
                
        except Exception as e:
            logger.error(f"❌ OKX 클라이언트 초기화 실패: {e}")
            raise
            from app.exchanges.okx.client import create_okx_client, OKXClient

            if self.api_credentials:
                # API 키가 있으면 create_okx_client 사용 (비동기)
                logger.info("🔑 API 키로 인증 클라이언트 생성 중...")

                try:
                    self.okx_client = await create_okx_client(
                        api_key=self.api_credentials['api_key'],
                        secret_key=self.api_credentials['secret_key'],
                        passphrase=self.api_credentials['passphrase'],
                        sandbox=True  # 안전을 위해 샌드박스 모드
                    )
                    logger.info("✅ OKX 인증 클라이언트 생성 완료")

                except Exception as auth_error:
                    logger.error(f"❌ 인증 클라이언트 생성 실패: {auth_error}")
                    logger.info("🔄 기본 클라이언트로 대체 시도...")

                    # 인증 실패시 기본 클라이언트 시도
                    self.okx_client = OKXClient()
                    logger.info("✅ 기본 OKX 클라이언트 생성 완료")

            else:
                # API 키가 없으면 기본 OKXClient 사용
                logger.info("🌐 기본 OKX 클라이언트 생성 중...")
                self.okx_client = OKXClient()  # 모든 파라미터가 선택사항
                logger.info("✅ OKX 기본 클라이언트 생성 완료")

            # 클라이언트 검증
            if self.okx_client is None:
                raise ValueError("OKX 클라이언트 생성 실패")

            logger.info(f"📊 생성된 클라이언트: {type(self.okx_client).__name__}")

            # 클라이언트 메서드 확인
            has_get_ticker = hasattr(self.okx_client, 'get_ticker')
            has_get_balance = hasattr(self.okx_client, 'get_account_balance')

            logger.info(f"📋 사용 가능한 기능:")
            logger.info(f"  - 시세 조회: {'✅' if has_get_ticker else '❌'}")
            logger.info(f"  - 잔고 조회: {'✅' if has_get_balance else '❌'}")

        except Exception as e:
            logger.error(f"❌ OKX 클라이언트 초기화 실패: {e}")

            # 최후의 수단: 간단한 공개 API 클라이언트
            logger.info("🔄 간단한 공개 API 클라이언트로 대체...")
            self.okx_client = SimpleOKXPublicClient()
            logger.info("✅ 공개 API 클라이언트 생성 완료")


class SimpleOKXPublicClient:
    """간단한 OKX 공개 API 클라이언트"""

    def __init__(self):
        self.base_url = "https://www.okx.com"
        logger.info("📡 공개 API 클라이언트 초기화")

    async def get_ticker(self, symbol: str):
        """시세 조회"""
        try:
            import requests

            logger.info(f"📊 {symbol} 시세 조회 중...")

            response = requests.get(
                f"{self.base_url}/api/v5/market/ticker?instId={symbol}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    ticker_data = data['data'][0]
                    result = {
                        'symbol': ticker_data['instId'],
                        'last': float(ticker_data['last']),
                        'bid': float(ticker_data['bidPx']),
                        'ask': float(ticker_data['askPx']),
                        'high': float(ticker_data['high24h']),
                        'low': float(ticker_data['low24h']),
                        'volume': float(ticker_data['vol24h']),
                        'timestamp': int(ticker_data['ts'])
                    }

                    logger.info(f"✅ {symbol} 시세: ${result['last']:,.2f}")
                    return result

            logger.warning(f"⚠️ {symbol} 시세 조회 실패")
            return None

        except Exception as e:
            logger.error(f"❌ {symbol} 시세 조회 오류: {e}")
            return None

    async def get_account_balance(self):
        """계좌 잔고 조회 (공개 API에서는 지원 안함)"""
        logger.warning("⚠️ 공개 API에서는 계좌 잔고 조회 불가")
        return None

    def __str__(self):
        return "SimpleOKXPublicClient"

    async def check_system_status(self):
        """시스템 상태 확인"""
        try:
            logger.info("🔍 시스템 상태 확인 중...")

            # 공개 API로 시세 조회 테스트
            await self.test_public_api()

            # API 키가 있으면 인증 API 테스트
            if self.okx_client:
                await self.test_private_api()

    async def check_system_status(self):
        """시스템 상태 확인"""
        try:
            logger.info("🔍 시스템 상태 확인 중...")

            # 공개 API로 시세 조회 테스트
            await self.test_public_api()

            # API 키가 있고 클라이언트가 정상이면 인증 API 테스트
            if self.okx_client and self.api_credentials:
                await self.test_private_api()
        except Exception as e:
            logger.error(f"❌ 시스템 상태 확인 실패: {e}")
            raise

        except Exception as e:
            logger.warning(f"⚠️ 시스템 상태 확인 중 오류: {e}")

    async def test_public_api(self):
        """공개 API 테스트"""
        try:
            import requests

            response = requests.get(
                "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    price = float(data['data'][0]['last'])
                    logger.info(f"📊 BTC-USDT 현재가: ${price:,.2f}")
                    logger.info("✅ OKX 공개 API 연결 정상")
                    return True

            logger.warning("⚠️ 공개 API 테스트 실패")
            return False

        except Exception as e:
            logger.warning(f"⚠️ 공개 API 테스트 오류: {e}")
            return False

    async def test_private_api(self):
        """인증 API 테스트"""
        try:
            if not self.okx_client or not hasattr(self.okx_client, 'get_account_balance'):
                logger.info("⚠️ 인증 API 테스트 건너뜀 (클라이언트 없음)")
                return False

            # 계좌 잔고 조회 테스트
            balance = await self.okx_client.get_account_balance()
            logger.info("✅ OKX 인증 API 연결 정상")

            # 잔고 정보 출력
            if balance and 'data' in balance:
                for account in balance['data']:
                    for detail in account.get('details', []):
                        currency = detail.get('ccy')
                        available = float(detail.get('availBal', 0))
                        if available > 0:
                            logger.info(f"💰 {currency} 잔고: {available}")

            return True

        except Exception as e:
            logger.warning(f"⚠️ 인증 API 테스트 실패: {e}")
            return False

    async def test_public_api(self):
        """공개 API 테스트"""
        try:
            import requests

            response = requests.get(
                "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    price = float(data['data'][0]['last'])
                    logger.info(f"📊 BTC-USDT 현재가: ${price:,.2f}")
                    logger.info("✅ OKX 공개 API 연결 정상")
                    return True

            logger.warning("⚠️ 공개 API 테스트 실패")
            return False

        except Exception as e:
            logger.warning(f"⚠️ 공개 API 테스트 오류: {e}")
            return False

    async def test_private_api(self):
        """인증 API 테스트"""
        try:
            if not self.okx_client:
                return False

            # 계좌 잔고 조회 테스트
            if hasattr(self.okx_client, 'get_account_balance'):
                balance = await self.okx_client.get_account_balance()
                logger.info("✅ OKX 인증 API 연결 정상")

                # 잔고 정보 출력
                if balance and 'data' in balance:
                    for account in balance['data']:
                        for detail in account.get('details', []):
                            currency = detail.get('ccy')
                            available = float(detail.get('availBal', 0))
                            if available > 0:
                                logger.info(f"💰 {currency} 잔고: {available}")

                return True
            else:
                logger.warning("⚠️ 계좌 잔고 조회 메서드 없음")
                return False

        except Exception as e:
            logger.warning(f"⚠️ 인증 API 테스트 실패: {e}")
            return False

    async def create_dantaro_bot(self, capital: float = 20.0, symbol: str = "BTC-USDT") -> int:
        """정확한 구조로 단타로 봇 생성"""
        try:
            logger.info(f"🤖 단타로 봇 생성: {symbol}, 자본금 ${capital}")

            # 봇 ID 생성
            bot_id = self.next_bot_id
            self.next_bot_id += 1

            # DantaroOKXSpotV1에 필요한 bot_config 구성
            bot_config = {
                # 기본 정보
                'bot_id': bot_id,
                'user_id': self.user_id,
                'symbol': symbol,
                'capital': capital,
                'exchange': 'okx',
                'strategy': 'dantaro_okx_spot_v1',

                # 단타로 전략 설정
                'grid_count': 5,  # 보수적
                'grid_gap': 1.0,  # 1%
                'multiplier': 1.5,  # 1.5배
                'profit_target': 1.0,  # 1% 익절
                'stop_loss': -5.0,  # 5% 손절
                'base_amount': capital / 5,  # 기본 주문 금액
                'min_amount': 5.0,  # 최소 주문 금액
                'initial_amount': capital,

                # 리스크 관리
                'max_orders': 5,
                'max_loss_per_trade': capital * 0.02,  # 2%
                'max_daily_loss': capital * 0.05,  # 5%

                # OKX 클라이언트 설정 (수정됨)
                'exchange_client': self.okx_client,  # None이면 시뮬레이션 모드
                'sandbox_mode': True,

                # 클라이언트 상태 정보
                'has_api_keys': self.api_credentials is not None,
                'client_type': type(self.okx_client).__name__ if self.okx_client else 'None'
            }

            logger.info("📋 봇 설정 생성 완료:")
            logger.info(f"  - 그리드 수: {bot_config['grid_count']}")
            logger.info(f"  - 그리드 간격: {bot_config['grid_gap']}%")
            logger.info(f"  - 물량 배수: {bot_config['multiplier']}x")
            logger.info(f"  - 익절 목표: {bot_config['profit_target']}%")
            logger.info(f"  - 손절선: {bot_config['stop_loss']}%")
            logger.info(f"  - 클라이언트: {bot_config['client_type']}")
            logger.info(
                f"  - API 키: {'있음' if bot_config['has_api_keys'] else '없음'}")

            # 클라이언트 상태 검증
            if self.okx_client is None:
                logger.warning("⚠️ OKX 클라이언트가 None입니다 - 시뮬레이션 모드로 진행")
                bot_config['simulation_mode'] = True
            else:
                logger.info(f"✅ OKX 클라이언트 준비됨: {type(self.okx_client)}")
                bot_config['simulation_mode'] = False

            # DantaroOKXSpotV1 전략 생성 (정확한 시그니처 사용)
            from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1
            strategy = DantaroOKXSpotV1(bot_config)

            logger.info("✅ DantaroOKXSpotV1 전략 생성 완료")

            # BotRunner 생성 (정확한 시그니처 사용)
            from app.bot_engine.core.bot_runner import BotRunner
            bot_runner = BotRunner(
                bot_id=bot_id,
                user_id=self.user_id,
                config=bot_config
            )

            logger.info("✅ BotRunner 생성 완료")

            # 봇 정보 저장
            self.active_bots[bot_id] = {
                'bot_runner': bot_runner,
                'strategy': strategy,
                'config': bot_config,
                'status': 'created',
                'created_at': datetime.now()
            }

            logger.info(f"🎯 봇 생성 완료: Bot ID {bot_id}")
            return bot_id

        except Exception as e:
            logger.error(f"❌ 봇 생성 실패: {e}")
            raise

    async def start_bot(self, bot_id: int) -> bool:
        """봇 시작"""
        try:
            if bot_id not in self.active_bots:
                raise ValueError(f"봇 ID {bot_id}를 찾을 수 없습니다")

            bot_info = self.active_bots[bot_id]
            config = bot_info['config']

            logger.info(f"▶️ 봇 시작 준비: Bot ID {bot_id}")

            # 실거래 확인
            if self.api_credentials:
                confirm = input(f"""
🚨 실거래 봇 시작 확인 🚨

봇 ID: {bot_id}
심볼: {config['symbol']}
자본금: ${config['capital']}
전략: 단타로 (보수적 설정)
모드: {'샌드박스' if config.get('sandbox_mode') else '실거래'}

⚠️ 설정된 API 키로 실제 거래가 실행됩니다!
⚠️ 손실 위험이 있습니다!

정말 시작하시겠습니까? (yes/no): """)

                if confirm.lower() != 'yes':
                    logger.info("❌ 사용자가 봇 시작을 취소했습니다")
                    return False

            # BotRunner로 봇 시작
            bot_runner = bot_info['bot_runner']

            logger.info("🚀 BotRunner.run() 실행 중...")

            # BotRunner의 run 메서드 실행
            if hasattr(bot_runner, 'run'):
                # 비동기 실행
                result = await bot_runner.run()

                if result:
                    bot_info['status'] = 'running'
                    bot_info['started_at'] = datetime.now()
                    logger.info(f"✅ 봇 시작 성공: Bot ID {bot_id}")
                    return True
                else:
                    logger.error(f"❌ 봇 시작 실패: Bot ID {bot_id}")
                    return False
            else:
                logger.error("❌ BotRunner.run 메서드를 찾을 수 없습니다")
                return False

        except Exception as e:
            logger.error(f"❌ 봇 시작 오류: {e}")
            return False

    async def monitor_bot(self, bot_id: int, duration: int = 300):
        """봇 모니터링"""
        try:
            if bot_id not in self.active_bots:
                raise ValueError(f"봇 ID {bot_id}를 찾을 수 없습니다")

            logger.info(f"👀 봇 모니터링 시작: Bot ID {bot_id} ({duration}초)")

            bot_runner = self.active_bots[bot_id]['bot_runner']
            start_time = time.time()
            end_time = start_time + duration

            while time.time() < end_time:
                try:
                    # BotRunner 상태 확인
                    if hasattr(bot_runner, 'get_status'):
                        status = bot_runner.get_status()
                        logger.info(f"📊 봇 상태: {status}")

                    # 성능 정보 확인
                    if hasattr(bot_runner, 'get_performance'):
                        performance = bot_runner.get_performance()
                        if performance:
                            logger.info(f"📈 성능 정보: {performance}")

                    # 실행 중인지 확인
                    if hasattr(bot_runner, 'is_running'):
                        is_running = bot_runner.is_running()
                        if not is_running:
                            logger.info("⏹️ 봇이 중지되었습니다")
                            break

                    # 30초마다 체크
                    await asyncio.sleep(30)

                except Exception as e:
                    logger.warning(f"⚠️ 모니터링 중 오류: {e}")
                    await asyncio.sleep(10)

            logger.info(f"✅ 모니터링 완료: Bot ID {bot_id}")

        except Exception as e:
            logger.error(f"❌ 모니터링 실패: {e}")

    async def stop_bot(self, bot_id: int) -> bool:
        """봇 중지"""
        try:
            if bot_id not in self.active_bots:
                raise ValueError(f"봇 ID {bot_id}를 찾을 수 없습니다")

            bot_runner = self.active_bots[bot_id]['bot_runner']

            logger.info(f"⏹️ 봇 중지 요청: Bot ID {bot_id}")

            # 우아한 중지 시도
            if hasattr(bot_runner, 'request_graceful_stop'):
                await bot_runner.request_graceful_stop()
                logger.info("✅ 우아한 중지 요청 완료")
            elif hasattr(bot_runner, 'stop'):
                await bot_runner.stop()
                logger.info("✅ 강제 중지 완료")
            else:
                logger.warning("⚠️ 중지 메서드를 찾을 수 없습니다")
                return False

            self.active_bots[bot_id]['status'] = 'stopped'
            self.active_bots[bot_id]['stopped_at'] = datetime.now()

            return True

        except Exception as e:
            logger.error(f"❌ 봇 중지 실패: {e}")
            return False

    def get_bot_summary(self):
        """봇 현황 요약"""
        logger.info("\n" + "="*60)
        logger.info("🤖 봇 현황 요약")
        logger.info("="*60)

        if not self.active_bots:
            logger.info("활성 봇이 없습니다.")
            return

        for bot_id, bot_info in self.active_bots.items():
            config = bot_info['config']

            logger.info(f"\n🤖 Bot ID: {bot_id}")
            logger.info(f"상태: {bot_info['status']}")
            logger.info(f"심볼: {config['symbol']}")
            logger.info(f"자본금: ${config['capital']}")
            logger.info(f"전략: {config['strategy']}")
            logger.info(
                f"생성 시간: {bot_info['created_at'].strftime('%H:%M:%S')}")

            if 'started_at' in bot_info:
                logger.info(
                    f"시작 시간: {bot_info['started_at'].strftime('%H:%M:%S')}")

            if 'stopped_at' in bot_info:
                logger.info(
                    f"종료 시간: {bot_info['stopped_at'].strftime('%H:%M:%S')}")


async def main():
    """메인 실행 함수"""
    manager = StructureBasedTradingManager()

    try:
        # 1. 시스템 초기화
        await manager.initialize()

        # 2. 단타로 봇 생성
        bot_id = await manager.create_dantaro_bot(
            capital=20.0,
            symbol="BTC-USDT"
        )

        # 3. 봇 시작
        success = await manager.start_bot(bot_id)

        if success:
            # 4. 봇 모니터링 (5분간)
            await manager.monitor_bot(bot_id, duration=300)

            # 5. 봇 중지 확인
            stop_confirm = input("봇을 중지하시겠습니까? (yes/no): ")
            if stop_confirm.lower() == 'yes':
                await manager.stop_bot(bot_id)

        # 6. 최종 요약
        manager.get_bot_summary()

    except Exception as e:
        logger.error(f"❌ 실행 중 오류: {e}")
        raise

    finally:
        logger.info("👋 프로그램 종료")

if __name__ == "__main__":
    print("🚀 오토블리츠 구조 기반 실거래 봇")
    print("기존 모듈의 정확한 구조 분석 결과 적용")
    print("-" * 60)

    asyncio.run(main())
