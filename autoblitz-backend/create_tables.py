#!/usr/bin/env python3
"""
데이터베이스 테이블 생성 스크립트
"""

import asyncio
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def create_tables():
    try:
        print("🔧 AutoBlitz 테이블 생성 시작...")

        # 1. 기본 설정 로드
        from app.core.config import get_settings
        settings = get_settings()
        print(f"✅ 설정 로드 완료: {settings.APP_NAME} v{settings.APP_VERSION}")

        # 2. 데이터베이스 엔진 로드
        from app.core.database import Base, engine
        print(f"✅ 데이터베이스 연결: {settings.DATABASE_URL}")

        # 3. 모델들 import (테이블 등록을 위해 필요)
        from app.models.user import User
        print("✅ User 모델 로드")

        from app.models.bot import Bot, BotStatus
        print("✅ Bot 모델 로드")

        from app.models.trade import Trade
        print("✅ Trade 모델 로드")

        # 4. 테이블 생성
        print("🔨 기존 테이블 삭제 중...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("🔨 새 테이블 생성 중...")
            await conn.run_sync(Base.metadata.create_all)

        await engine.dispose()
        print("🎉 테이블 생성 완료!")
        return True

    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        print("💡 누락된 모델이나 함수가 있습니다.")
        return False
    except Exception as e:
        print(f"❌ 기타 오류: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(create_tables())
    if success:
        print("\n✅ 다음 단계: python -m uvicorn app.main:app --reload")
    else:
        print("\n🔧 오류를 수정한 후 다시 시도해주세요.")
