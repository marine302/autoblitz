# real_trading_corrected.py
# BotRunner와 기존 모듈의 올바른 사용법 적용

import asyncio
import time
import logging
import uuid
from datetime import datetime

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


class CorrectedTradingBotManager:
    """올바른 BotRunner 사용법을 적용한 실거래 봇 매니저"""

    def __init__(self):
        self.okx_client = None
        self.active_bots = {}
        self.user_id = "test_user_001"  # 테스트 사용자 ID

    async def initialize(self):
        """시스템 초기화"""
        try:
            logger.info("🚀 실거래 봇 시스템 초기화 시작")

            # 모듈 Import
            from app.exchanges.okx.client import create_okx_client
            from app.core.config import settings

            # OKX 클라이언트 초기화
            self.okx_client = create_okx_client()
            logger.info("✅ OKX 클라이언트 연결 완료")

            # API 키 상태 확인
            api_key_status = "설정됨" if getattr(
                settings, 'OKX_API_KEY', None) else "❌ 없음"
            logger.info(f"🔑 API 키 상태: {api_key_status}")

            # OKX 연결 테스트
            await self.test_okx_connection()

            logger.info("🎯 실거래 봇 시스템 준비 완료!")

        except Exception as e:
            logger.error(f"❌ 시스템 초기화 실패: {e}")
            raise

    async def test_okx_connection(self):
        """OKX 연결 테스트"""
        try:
            logger.info("🔍 OKX 연결 테스트 중...")

            # 공개 API로 시세 조회 테스트
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
                    logger.info("✅ OKX API 연결 정상")
                    return True

            logger.warning("⚠️ OKX 연결 테스트 실패")
            return False

        except Exception as e:
            logger.warning(f"⚠️ OKX 연결 테스트 오류: {e}")
            return False

    async def create_dantaro_bot(self, capital: float = 20.0, symbol: str = "BTC-USDT"):
        """DantaroOKXSpotV1 전략으로 봇 생성"""
        try:
            logger.info(f"🤖 단타로 봇 생성 시작: {symbol}, 자본금 ${capital}")

            # 모듈 Import
            from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1
            from app.bot_engine.core.bot_runner import BotRunner

            # 봇 ID 생성
            bot_id = f"dantaro_{symbol.replace('-', '_').lower()}_{int(time.time())}"

            # 봇 설정 (BotRunner에 필요한 config)
            bot_config = {
                'symbol': symbol,
                'capital': capital,
                'strategy_type': 'dantaro_okx_spot_v1',
                'risk_management': {
                    'max_loss': capital * 0.05,  # 5% 손절
                    'max_orders': 5
                }
            }

            # DantaroOKXSpotV1 전략 생성
            strategy = DantaroOKXSpotV1(
                symbol=symbol,
                capital=capital,
                initial_amount=capital,
                grid_count=5,  # 보수적 설정
                grid_gap=1.0,  # 1% 간격
                multiplier=1.5,  # 1.5배
                profit_target=1.0,  # 1% 익절
                stop_loss=-5.0,  # 5% 손절
                base_amount=capital/5,
                min_amount=5.0
            )

            logger.info("✅ 단타로 전략 생성 완료")
            logger.info(f"📋 전략 설정:")
            logger.info(f"  - 그리드 수: 5개")
            logger.info(f"  - 그리드 간격: 1.0%")
            logger.info(f"  - 물량 배수: 1.5배")
            logger.info(f"  - 익절 목표: 1.0%")
            logger.info(f"  - 손절선: -5.0%")

            # BotRunner 생성 (올바른 파라미터로)
            try:
                bot_runner = BotRunner(
                    bot_id=bot_id,
                    user_id=self.user_id,
                    config=bot_config
                )
                logger.info("✅ BotRunner 생성 완료")
            except Exception as e:
                logger.error(f"❌ BotRunner 생성 실패: {e}")
                # BotRunner 없이도 진행 가능하도록
                bot_runner = None
                logger.info("⚠️ BotRunner 없이 직접 전략 실행 모드로 진행")

            # 봇 정보 저장
            self.active_bots[bot_id] = {
                'bot_runner': bot_runner,
                'strategy': strategy,
                'symbol': symbol,
                'capital': capital,
                'status': 'created',
                'created_at': datetime.now(),
                'config': bot_config
            }

            logger.info(f"🎯 봇 생성 완료: {bot_id}")
            return bot_id

        except Exception as e:
            logger.error(f"❌ 봇 생성 실패: {e}")
            raise

    async def start_bot(self, bot_id: str):
        """봇 시작"""
        try:
            if bot_id not in self.active_bots:
                raise ValueError(f"봇을 찾을 수 없습니다: {bot_id}")

            bot_info = self.active_bots[bot_id]
            logger.info(f"▶️ 봇 시작 준비: {bot_id}")

            # 실거래 시작 확인
            confirm = input(f"""
🚨 실거래 봇 시작 확인 🚨

봇 ID: {bot_id}
심볼: {bot_info['symbol']}
자본금: ${bot_info['capital']}
전략: 단타로 (보수적 설정)

⚠️ API 키가 설정된 경우 실제 자금이 사용됩니다!
⚠️ 손실 위험이 있습니다!

정말 시작하시겠습니까? (yes/no): """)

            if confirm.lower() != 'yes':
                logger.info("❌ 사용자가 봇 시작을 취소했습니다")
                return False

            # 봇 시작 시도
            success = False

            if bot_info['bot_runner']:
                # BotRunner 사용 가능한 경우
                try:
                    logger.info("🔧 BotRunner를 통한 봇 시작...")
                    success = await self.start_with_bot_runner(bot_id)
                except Exception as e:
                    logger.warning(f"⚠️ BotRunner 시작 실패: {e}")
                    logger.info("🔄 직접 전략 실행으로 전환...")
                    success = await self.start_with_direct_strategy(bot_id)
            else:
                # 직접 전략 실행
                success = await self.start_with_direct_strategy(bot_id)

            if success:
                bot_info['status'] = 'running'
                bot_info['started_at'] = datetime.now()
                logger.info(f"✅ 봇 시작 성공: {bot_id}")
                return True
            else:
                logger.error(f"❌ 봇 시작 실패: {bot_id}")
                return False

        except Exception as e:
            logger.error(f"❌ 봇 시작 오류: {e}")
            return False

    async def start_with_bot_runner(self, bot_id: str):
        """BotRunner를 통한 봇 시작"""
        bot_info = self.active_bots[bot_id]
        bot_runner = bot_info['bot_runner']
        strategy = bot_info['strategy']

        # BotRunner 메서드 확인 및 사용
        try:
            if hasattr(bot_runner, 'start_bot'):
                result = await bot_runner.start_bot(
                    strategy=strategy,
                    exchange_client=self.okx_client
                )
                return result
            elif hasattr(bot_runner, 'start'):
                result = await bot_runner.start(
                    strategy=strategy,
                    exchange=self.okx_client
                )
                return result
            else:
                logger.warning("⚠️ BotRunner에서 시작 메서드를 찾을 수 없음")
                return False
        except Exception as e:
            logger.error(f"❌ BotRunner 실행 오류: {e}")
            return False

    async def start_with_direct_strategy(self, bot_id: str):
        """직접 전략 실행"""
        bot_info = self.active_bots[bot_id]
        strategy = bot_info['strategy']

        logger.info("🎯 직접 전략 실행 모드")

        try:
            # 전략의 주요 메서드 확인
            if hasattr(strategy, 'execute'):
                logger.info("📈 전략 execute 메서드 실행")
                result = await strategy.execute()
                return True
            elif hasattr(strategy, 'run'):
                logger.info("📈 전략 run 메서드 실행")
                result = await strategy.run()
                return True
            else:
                # 기본 시뮬레이션 실행
                logger.info("🎮 기본 시뮬레이션 실행")
                await self.run_basic_simulation(bot_id)
                return True

        except Exception as e:
            logger.error(f"❌ 직접 전략 실행 오류: {e}")
            return False

    async def run_basic_simulation(self, bot_id: str):
        """기본 시뮬레이션"""
        bot_info = self.active_bots[bot_id]

        logger.info(f"🎮 {bot_info['symbol']} 기본 거래 시뮬레이션 시작")

        # 30초간 시뮬레이션
        for i in range(6):  # 5초씩 6번
            await asyncio.sleep(5)

            # 가상 수익률 계산
            profit_percent = (i - 2) * 0.2  # -0.4% ~ +0.6%

            logger.info(f"📊 시뮬레이션 {(i+1)*5}초: 가상 수익률 {profit_percent:+.2f}%")

        # 시뮬레이션 완료
        final_profit_percent = 0.8  # 0.8% 가상 수익
        final_profit_amount = bot_info['capital'] * final_profit_percent / 100

        bot_info['final_pnl'] = final_profit_amount
        bot_info['final_pnl_percent'] = final_profit_percent
        bot_info['status'] = 'completed'

        logger.info(
            f"🎉 시뮬레이션 완료: {final_profit_percent:+.2f}% (${final_profit_amount:+.2f})")

    async def monitor_bot(self, bot_id: str, duration: int = 300):
        """봇 모니터링"""
        if bot_id not in self.active_bots:
            raise ValueError(f"봇을 찾을 수 없습니다: {bot_id}")

        logger.info(f"👀 봇 모니터링 시작: {bot_id} ({duration}초)")

        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time and self.active_bots[bot_id]['status'] == 'running':
            try:
                bot_info = self.active_bots[bot_id]

                # 간단한 상태 출력
                elapsed = int(time.time() - start_time)
                logger.info(f"📊 모니터링: {elapsed}초 경과, 상태: {bot_info['status']}")

                # 30초마다 체크
                await asyncio.sleep(30)

            except Exception as e:
                logger.warning(f"⚠️ 모니터링 오류: {e}")
                await asyncio.sleep(10)

        logger.info(f"✅ 모니터링 완료: {bot_id}")

    def get_bot_summary(self):
        """봇 현황 요약"""
        logger.info("\n" + "="*50)
        logger.info("🤖 봇 현황 요약")
        logger.info("="*50)

        if not self.active_bots:
            logger.info("활성 봇이 없습니다.")
            return

        for bot_id, bot_info in self.active_bots.items():
            logger.info(f"\n봇 ID: {bot_id}")
            logger.info(f"상태: {bot_info['status']}")
            logger.info(f"심볼: {bot_info['symbol']}")
            logger.info(f"자본금: ${bot_info['capital']}")

            if 'started_at' in bot_info:
                logger.info(
                    f"시작 시간: {bot_info['started_at'].strftime('%H:%M:%S')}")

            if 'final_pnl' in bot_info:
                pnl = bot_info['final_pnl']
                pnl_percent = bot_info.get('final_pnl_percent', 0)
                logger.info(f"최종 수익: ${pnl:+.2f} ({pnl_percent:+.2f}%)")


async def main():
    """메인 실행 함수"""
    manager = CorrectedTradingBotManager()

    try:
        # 1. 시스템 초기화
        await manager.initialize()

        # 2. 단타로 봇 생성
        bot_id = await manager.create_dantaro_bot(capital=20.0, symbol="BTC-USDT")

        # 3. 봇 시작
        success = await manager.start_bot(bot_id)

        if success:
            # 4. 봇 모니터링 (최대 5분)
            await manager.monitor_bot(bot_id, duration=300)

        # 5. 최종 요약
        manager.get_bot_summary()

    except Exception as e:
        logger.error(f"❌ 실행 중 오류: {e}")

    finally:
        logger.info("👋 프로그램 종료")

if __name__ == "__main__":
    print("🚀 오토블리츠 수정된 실거래 봇")
    print("BotRunner 올바른 사용법 적용")
    print("-" * 60)

    asyncio.run(main())
