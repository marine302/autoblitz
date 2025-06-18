#!/bin/bash
echo "🚀 오토블리츠 프로젝트 구조 분석"
echo "================================="
echo

echo "📁 1. 디렉토리 구조:"
tree -I "__pycache__|*.pyc|node_modules" -L 2 || find . -type d | head -20

echo
echo "📝 2. Python 파일 개수:"
find . -name "*.py" | wc -l
echo "   주요 모듈들:"
find app/ -name "*.py" 2>/dev/null | wc -l && echo "   app/ 모듈"
find . -name "*bot*" | wc -l && echo "   봇 관련 파일"
find . -name "*okx*" | wc -l && echo "   OKX 관련 파일"

echo
echo "🗄️ 3. 데이터베이스:"
ls -lh *.db 2>/dev/null || echo "   데이터베이스 파일 없음"

echo
echo "🚀 4. 서버 상태:"
if curl -s http://localhost:8000/health > /dev/null; then
  echo "   ✅ FastAPI 서버 실행 중"
else
  echo "   ❌ FastAPI 서버 중지됨"
fi

echo
echo "📦 5. 주요 설정 파일:"
ls -la *.env *.json *.txt *.yml *.yaml 2>/dev/null | head -5

echo
echo "분석 완료! 🎉"
