"""
데이터베이스 연결 및 세션 관리 (비동기/동기 지원)
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from app.core.config import get_settings

settings = get_settings()

# 비동기 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # DEBUG 모드일 때만 SQL 로깅
    future=True
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 기존 코드 호환성을 위한 동기식 엔진 및 세션 (SQLite의 경우)
sync_database_url = settings.DATABASE_URL.replace("+aiosqlite", "")
sync_engine = create_engine(
    sync_database_url,
    echo=settings.DEBUG,
    connect_args={
        "check_same_thread": False} if "sqlite" in sync_database_url else {}
)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=sync_engine)

# 모델 베이스 클래스
Base = declarative_base()

# 비동기 세션 의존성


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    비동기 데이터베이스 세션 의존성

    FastAPI의 Depends와 함께 사용:
    async def my_route(db: AsyncSession = Depends(get_async_session)):
        # 비동기 작업 수행
        result = await db.execute(query)

    컨텍스트 매니저로 세션을 자동으로 관리하므로 수동으로 close할 필요가 없습니다.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 레거시 코드 지원용 동기식 세션


def get_db():
    """
    레거시 지원용 동기식 데이터베이스 세션
    새로운 코드에서는 get_async_session을 사용하세요.

    FastAPI의 Depends와 함께 사용:
    def my_route(db: Session = Depends(get_db)):
        # 동기식 작업 수행
        result = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
