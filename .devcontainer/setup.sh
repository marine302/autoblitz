#!/bin/bash

echo "🚀 AutoBlitz 개발 환경 설정 시작..."

# Python 패키지 설치
echo "📦 Python 패키지 설치 중..."
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy alembic
pip install boto3 redis celery python-jose[cryptography]
pip install httpx websockets python-multipart
pip install pytest pytest-asyncio black flake8

# 프로젝트 디렉토리 구조 생성
echo "📁 프로젝트 구조 생성 중..."
mkdir -p autoblitz-backend/{app,tests,scripts}
mkdir -p autoblitz-frontend/{src,public}
mkdir -p autoblitz-infrastructure/{cloudformation,terraform}

# 기본 파일 생성
echo "📝 기본 파일 생성 중..."

# Backend requirements.txt
cat > autoblitz-backend/requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
boto3==1.29.7
redis==5.0.1
celery==5.3.4
python-jose[cryptography]==3.3.0
httpx==0.25.2
websockets==12.0
python-multipart==0.0.6
python-dotenv==1.0.0
pydantic-settings==2.1.0
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
EOF

# Frontend package.json
cat > autoblitz-frontend/package.json << EOF
{
  "name": "autoblitz-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "socket.io-client": "^4.7.2",
    "recharts": "^2.10.3",
    "zustand": "^4.4.7",
    "@headlessui/react": "^1.7.17",
    "tailwindcss": "^3.3.6"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  }
}
EOF

# 환경 변수 템플릿
cat > .env.example << EOF
# Application
APP_NAME=AutoBlitz
APP_VERSION=1.0.0
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/autoblitz

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# AWS
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Exchange APIs
OKX_API_KEY=your-okx-api-key
OKX_SECRET_KEY=your-okx-secret-key
OKX_PASSPHRASE=your-okx-passphrase

UPBIT_ACCESS_KEY=your-upbit-access-key
UPBIT_SECRET_KEY=your-upbit-secret-key
EOF

echo "✅ 개발 환경 설정 완료!"
echo "📌 다음 단계:"
echo "1. Codespace에서 터미널 열기"
echo "2. cd autoblitz-backend && pip install -r requirements.txt"
echo "3. cd ../autoblitz-frontend && npm install"
