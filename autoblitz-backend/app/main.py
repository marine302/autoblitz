"""
AutoBlitz API - 간단 버전
로컬 개발 및 테스트를 위한 FastAPI 백엔드 서버
"""

import logging
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoBlitz API",
    version="1.0.0",
    description="암호화폐 자동매매 봇 API - 로컬 테스트 버전"
)

# CORS 설정 - 개발 환경용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용. 프로덕션에서는 특정 도메인으로 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 추가 (단계적으로)
try:
    from app.api.v1 import bots
    app.include_router(bots.router, prefix="/api/v1/bots", tags=["bots"])
    logger.info("✅ Bots router added")
except Exception as e:
    logger.error(f"❌ Bots router error: {str(e)}")
    logger.error(traceback.format_exc())

try:
    from app.api.v1 import auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    logger.info("✅ Auth router added")
except Exception as e:
    logger.error(f"❌ Auth router error: {str(e)}")
    logger.error(traceback.format_exc())

try:
    from app.api.v1 import users
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    logger.info("✅ Users router added")
except Exception as e:
    logger.error(f"❌ Users router error: {str(e)}")
    logger.error(traceback.format_exc())


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "AutoBlitz",
        "version": "1.0.0",
        "description": "AI 기반 암호화폐 자동매매 시스템",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "AutoBlitz API"
    }


@app.get("/test")
async def test():
    """테스트 엔드포인트"""
    return {
        "message": "API 테스트 성공",
        "mode": "로컬 테스트",
        "available_routes": [
            "/api/v1/bots",
            "/api/v1/auth",
            "/api/v1/users"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    # 로컬 테스트를 위한 서버 설정
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 코드 변경 시 자동 리로드
        log_level="info"
    )
