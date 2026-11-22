#!/bin/bash
# Docker + ngrok 자동 실행 스크립트

set -e

echo "🚀 Docker 컨테이너 시작 중..."
docker-compose up -d

echo "⏳ 컨테이너 시작 대기 중..."
sleep 5

# 헬스체크
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ 컨테이너가 정상적으로 실행 중입니다."
else
    echo "⚠️ 컨테이너가 아직 준비되지 않았습니다. 잠시 후 다시 시도하세요."
    exit 1
fi

echo ""
echo "🌐 ngrok 터널 생성 중..."
echo "접속 URL이 아래에 표시됩니다:"
echo ""

# ngrok 실행
ngrok http 8501

