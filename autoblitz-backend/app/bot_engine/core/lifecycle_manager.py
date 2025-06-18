# app/bot_engine/core/lifecycle_manager.py

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.bot import Bot, BotStatus
from app.models.trade import Trade
from app.core.database import get_async_session
from app.bot_engine.core.bot_runner import BotRunner
from app.services.exchange_service import ExchangeService

logger = logging.getLogger(__name__)


class BotAction(Enum):
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    FORCE_STOP = "force_stop"


@dataclass
class BotContext:
    """봇 실행 컨텍스트"""
    bot_id: int
    user_id: int
    exchange: str
    symbol: str
    strategy: str
    capital: float
    settings: dict
    runner: Optional[BotRunner] = None
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0


class BotLifecycleManager:
    """봇의 전체 생명주기를 관리하는 핵심 클래스"""
    
    def __init__(self):
        self.running_bots: Dict[int, BotContext] = {}
        self.exchange_service = ExchangeService()
        self._shutdown_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """생명주기 관리자 시작"""
        logger.info("봇 생명주기 관리자 시작")
        
        # 기존 실행 중인 봇들 복구
        await self._recover_running_bots()
        
        # 모니터링 태스크 시작
        self._monitor_task = asyncio.create_task(self._monitor_bots())
        
    async def stop(self):
        """생명주기 관리자 중지"""
        logger.info("봇 생명주기 관리자 중지 시작")
        
        self._shutdown_event.set()
        
        # 모든 실행 중인 봇 안전하게 중지
        await self._stop_all_bots()
        
        # 모니터링 태스크 중지
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("봇 생명주기 관리자 중지 완료")
        
    async def execute_bot_action(self, bot_id: int, action: BotAction, user_id: int) -> dict:
        """봇 액션 실행"""
        try:
            async with get_async_session() as session:
                # 봇 정보 조회
                result = await session.execute(
                    select(Bot).where(Bot.id == bot_id, Bot.user_id == user_id)
                )
                bot = result.scalar_one_or_none()
                
                if not bot:
                    return {"success": False, "error": "봇을 찾을 수 없습니다"}
                
                if action == BotAction.START:
                    return await self._start_bot(bot, session)
                elif action == BotAction.STOP:
                    return await self._stop_bot(bot_id, session)
                elif action == BotAction.PAUSE:
                    return await self._pause_bot(bot_id, session)
                elif action == BotAction.RESUME:
                    return await self._resume_bot(bot_id, session)
                elif action == BotAction.FORCE_STOP:
                    return await self._force_stop_bot(bot_id, session)
                else:
                    return {"success": False, "error": "지원하지 않는 액션입니다"}
                    
        except Exception as e:
            logger.error(f"봇 액션 실행 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _start_bot(self, bot: Bot, session: AsyncSession) -> dict:
        """봇 시작"""
        try:
            # 이미 실행 중인 봇인지 확인
            if bot.id in self.running_bots:
                return {"success": False, "error": "이미 실행 중인 봇입니다"}
            
            # 봇 상태가 시작 가능한지 확인
            if bot.status not in [BotStatus.CREATED, BotStatus.STOPPED, BotStatus.ERROR]:
                return {"success": False, "error": f"현재 상태({bot.status})에서는 시작할 수 없습니다"}
            
            # 사용자 거래소 설정 확인
            user_api_keys = await self._get_user_api_keys(bot.user_id, bot.exchange)
            if not user_api_keys:
                return {"success": False, "error": "거래소 API 키가 설정되지 않았습니다"}
            
            # BotContext 생성
            context = BotContext(
                bot_id=bot.id,
                user_id=bot.user_id,
                exchange=bot.exchange,
                symbol=bot.symbol,
                strategy=bot.strategy,
                capital=float(bot.capital),
                settings=bot.settings or {}
            )
            
            # BotRunner 생성 및 시작
            runner = BotRunner(context, user_api_keys)
            await runner.initialize()
            
            # 실행 중인 봇 목록에 추가
            context.runner = runner
            context.last_heartbeat = datetime.now(timezone.utc)
            self.running_bots[bot.id] = context
            
            # 데이터베이스 상태 업데이트
            await session.execute(
                update(Bot)
                .where(Bot.id == bot.id)
                .values(
                    status=BotStatus.RUNNING,
                    started_at=datetime.now(timezone.utc),
                    error_message=None
                )
            )
            await session.commit()
            
            # 백그라운드에서 봇 실행 시작
            asyncio.create_task(self._run_bot(context))
            
            logger.info(f"봇 {bot.id} 시작 완료")
            return {"success": True, "message": "봇이 성공적으로 시작되었습니다"}
            
        except Exception as e:
            logger.error(f"봇 시작 중 오류: {e}")
            # 오류 상태로 업데이트
            await session.execute(
                update(Bot)
                .where(Bot.id == bot.id)
                .values(
                    status=BotStatus.ERROR,
                    error_message=str(e)
                )
            )
            await session.commit()
            return {"success": False, "error": str(e)}
    
    async def _stop_bot(self, bot_id: int, session: AsyncSession) -> dict:
        """봇 안전하게 중지"""
        try:
            context = self.running_bots.get(bot_id)
            if not context:
                return {"success": False, "error": "실행 중이지 않은 봇입니다"}
            
            # 현재 포지션이 있는지 확인
            if context.runner:
                has_position = await context.runner.has_open_position()
                if has_position:
                    # 포지션이 있으면 현재 사이클 완료 후 중지
                    context.runner.request_graceful_stop()
                    status = BotStatus.STOPPING
                    message = "현재 사이클 완료 후 중지됩니다"
                else:
                    # 포지션이 없으면 즉시 중지
                    await context.runner.stop()
                    del self.running_bots[bot_id]
                    status = BotStatus.STOPPED
                    message = "봇이 성공적으로 중지되었습니다"
            else:
                del self.running_bots[bot_id]
                status = BotStatus.STOPPED
                message = "봇이 중지되었습니다"
            
            # 데이터베이스 상태 업데이트
            await session.execute(
                update(Bot)
                .where(Bot.id == bot_id)
                .values(
                    status=status,
                    stopped_at=datetime.now(timezone.utc) if status == BotStatus.STOPPED else None
                )
            )
            await session.commit()
            
            logger.info(f"봇 {bot_id} 중지 요청 완료")
            return {"success": True, "message": message}
            
        except Exception as e:
            logger.error(f"봇 중지 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _force_stop_bot(self, bot_id: int, session: AsyncSession) -> dict:
        """봇 강제 중지 (포지션 청산)"""
        try:
            context = self.running_bots.get(bot_id)
            if not context:
                return {"success": False, "error": "실행 중이지 않은 봇입니다"}
            
            # 모든 포지션 강제 청산
            if context.runner:
                await context.runner.force_close_all_positions()
                await context.runner.stop()
            
            # 실행 중인 봇 목록에서 제거
            del self.running_bots[bot_id]
            
            # 데이터베이스 상태 업데이트
            await session.execute(
                update(Bot)
                .where(Bot.id == bot_id)
                .values(
                    status=BotStatus.STOPPED,
                    stopped_at=datetime.now(timezone.utc),
                    error_message="사용자에 의해 강제 중지됨"
                )
            )
            await session.commit()
            
            logger.info(f"봇 {bot_id} 강제 중지 완료")
            return {"success": True, "message": "봇이 강제 중지되었습니다 (모든 포지션 청산)"}
            
        except Exception as e:
            logger.error(f"봇 강제 중지 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _pause_bot(self, bot_id: int, session: AsyncSession) -> dict:
        """봇 일시정지"""
        try:
            context = self.running_bots.get(bot_id)
            if not context or not context.runner:
                return {"success": False, "error": "실행 중이지 않은 봇입니다"}
            
            await context.runner.pause()
            
            await session.execute(
                update(Bot)
                .where(Bot.id == bot_id)
                .values(status=BotStatus.PAUSED)
            )
            await session.commit()
            
            return {"success": True, "message": "봇이 일시정지되었습니다"}
            
        except Exception as e:
            logger.error(f"봇 일시정지 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _resume_bot(self, bot_id: int, session: AsyncSession) -> dict:
        """봇 재개"""
        try:
            context = self.running_bots.get(bot_id)
            if not context or not context.runner:
                return {"success": False, "error": "일시정지된 봇을 찾을 수 없습니다"}
            
            await context.runner.resume()
            
            await session.execute(
                update(Bot)
                .where(Bot.id == bot_id)
                .values(status=BotStatus.RUNNING)
            )
            await session.commit()
            
            return {"success": True, "message": "봇이 재개되었습니다"}
            
        except Exception as e:
            logger.error(f"봇 재개 중 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_bot(self, context: BotContext):
        """개별 봇 실행 루프"""
        try:
            await context.runner.run()
        except Exception as e:
            logger.error(f"봇 {context.bot_id} 실행 중 오류: {e}")
            context.error_count += 1
            
            # 에러 횟수가 많으면 봇 중지
            if context.error_count >= 3:
                async with get_async_session() as session:
                    await session.execute(
                        update(Bot)
                        .where(Bot.id == context.bot_id)
                        .values(
                            status=BotStatus.ERROR,
                            error_message=f"연속 오류 발생: {str(e)}",
                            stopped_at=datetime.now(timezone.utc)
                        )
                    )
                    await session.commit()
                
                # 실행 목록에서 제거
                if context.bot_id in self.running_bots:
                    del self.running_bots[context.bot_id]
        finally:
            # 정상 종료 시에도 실행 목록에서 제거
            if context.bot_id in self.running_bots:
                del self.running_bots[context.bot_id]
    
    async def _monitor_bots(self):
        """실행 중인 봇들 모니터링"""
        while not self._shutdown_event.is_set():
            try:
                current_time = datetime.now(timezone.utc)
                dead_bots = []
                
                for bot_id, context in self.running_bots.items():
                    # 하트비트 확인 (5분 이상 응답 없으면 죽은 것으로 간주)
                    if context.last_heartbeat:
                        time_diff = (current_time - context.last_heartbeat).total_seconds()
                        if time_diff > 300:  # 5분
                            logger.warning(f"봇 {bot_id} 하트비트 타임아웃")
                            dead_bots.append(bot_id)
                    
                    # 러너 상태 확인
                    if context.runner and not context.runner.is_running():
                        logger.info(f"봇 {bot_id} 실행 완료")
                        dead_bots.append(bot_id)
                
                # 죽은 봇들 정리
                for bot_id in dead_bots:
                    await self._cleanup_dead_bot(bot_id)
                
                # 30초마다 확인
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"봇 모니터링 중 오류: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_dead_bot(self, bot_id: int):
        """죽은 봇 정리"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    update(Bot)
                    .where(Bot.id == bot_id)
                    .values(
                        status=BotStatus.ERROR,
                        error_message="봇 응답 없음 (타임아웃)",
                        stopped_at=datetime.now(timezone.utc)
                    )
                )
                await session.commit()
            
            if bot_id in self.running_bots:
                del self.running_bots[bot_id]
                
            logger.info(f"죽은 봇 {bot_id} 정리 완료")
            
        except Exception as e:
            logger.error(f"죽은 봇 {bot_id} 정리 중 오류: {e}")
    
    async def _recover_running_bots(self):
        """서버 재시작 시 실행 중이던 봇들 복구"""
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(Bot).where(Bot.status == BotStatus.RUNNING)
                )
                running_bots = result.scalars().all()
                
                for bot in running_bots:
                    logger.info(f"봇 {bot.id} 복구 중...")
                    
                    # 일단 STOPPED 상태로 변경 (사용자가 수동으로 재시작해야 함)
                    await session.execute(
                        update(Bot)
                        .where(Bot.id == bot.id)
                        .values(
                            status=BotStatus.STOPPED,
                            error_message="서버 재시작으로 인한 중지"
                        )
                    )
                
                await session.commit()
                logger.info(f"{len(running_bots)}개 봇 복구 완료")
                
        except Exception as e:
            logger.error(f"봇 복구 중 오류: {e}")
    
    async def _stop_all_bots(self):
        """모든 실행 중인 봇 중지"""
        tasks = []
        for bot_id in list(self.running_bots.keys()):
            task = asyncio.create_task(self._emergency_stop_bot(bot_id))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _emergency_stop_bot(self, bot_id: int):
        """긴급 봇 중지"""
        try:
            context = self.running_bots.get(bot_id)
            if context and context.runner:
                await context.runner.stop()
            
            if bot_id in self.running_bots:
                del self.running_bots[bot_id]
                
        except Exception as e:
            logger.error(f"긴급 봇 중지 중 오류 (봇 {bot_id}): {e}")
    
    async def _get_user_api_keys(self, user_id: int, exchange: str) -> Optional[dict]:
        """사용자 거래소 API 키 조회"""
        try:
            async with get_async_session() as session:
                # User 모델에서 API 키 정보 조회
                # 실제 구현에서는 암호화된 API 키를 복호화해야 함
                from app.models.user import User
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return None
                
                # 거래소별 API 키 반환
                if exchange.lower() == "okx":
                    return {
                        "api_key": user.okx_api_key,
                        "secret_key": user.okx_secret_key,
                        "passphrase": user.okx_passphrase
                    }
                elif exchange.lower() == "upbit":
                    return {
                        "access_key": user.upbit_access_key,
                        "secret_key": user.upbit_secret_key
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"API 키 조회 중 오류: {e}")
            return None
    
    def get_running_bot_stats(self) -> dict:
        """실행 중인 봇 통계"""
        return {
            "total_running": len(self.running_bots),
            "bots": [
                {
                    "bot_id": context.bot_id,
                    "user_id": context.user_id,
                    "exchange": context.exchange,
                    "symbol": context.symbol,
                    "strategy": context.strategy,
                    "last_heartbeat": context.last_heartbeat.isoformat() if context.last_heartbeat else None,
                    "error_count": context.error_count
                }
                for context in self.running_bots.values()
            ]
        }


# 글로벌 인스턴스
bot_lifecycle_manager = BotLifecycleManager()