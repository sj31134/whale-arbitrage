#!/bin/bash
# 프로덕션 배포 스크립트

set -e

echo "🚀 프로덕션 배포 시작..."

# 환경 확인
if [ ! -f "data/project.db" ]; then
    echo "⚠️ 경고: data/project.db 파일이 없습니다."
    echo "   데이터베이스는 볼륨으로 마운트되므로 서버에 파일이 있어야 합니다."
fi

if [ ! -f "config/.env" ]; then
    echo "⚠️ 경고: config/.env 파일이 없습니다."
    echo "   환경 변수 파일이 필요합니다."
fi

# 기존 컨테이너 중지 및 제거
if [ "$(docker ps -aq -f name=arbitrage-ui-prod)" ]; then
    echo "기존 컨테이너 중지 및 제거 중..."
    docker stop arbitrage-ui-prod || true
    docker rm arbitrage-ui-prod || true
fi

# 프로덕션 설정으로 배포
echo "Docker Compose (프로덕션)로 배포 중..."
docker-compose -f docker-compose.prod.yml up -d --build

echo ""
echo "✅ 배포 완료!"
echo ""
echo "📊 서비스 상태:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "🌐 접속 URL:"
echo "  http://localhost:8501"
echo "  또는 http://[서버IP]:8501"
echo ""
echo "📋 로그 확인:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 중지:"
echo "  docker-compose -f docker-compose.prod.yml down"

