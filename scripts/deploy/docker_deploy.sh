#!/bin/bash
# Docker 배포 스크립트

set -e

echo "🚀 Docker 배포 시작..."

# 기존 컨테이너 중지 및 제거
if [ "$(docker ps -aq -f name=arbitrage-ui)" ]; then
    echo "기존 컨테이너 중지 및 제거 중..."
    docker stop arbitrage-ui || true
    docker rm arbitrage-ui || true
fi

# Docker Compose로 배포
if [ -f "docker-compose.yml" ]; then
    echo "Docker Compose로 배포 중..."
    docker-compose up -d --build
    
    echo ""
    echo "✅ 배포 완료!"
    echo ""
    echo "📊 서비스 상태:"
    docker-compose ps
    
    echo ""
    echo "🌐 접속 URL:"
    echo "  http://localhost:8501"
    echo ""
    echo "📋 로그 확인:"
    echo "  docker-compose logs -f"
else
    echo "❌ docker-compose.yml 파일을 찾을 수 없습니다."
    exit 1
fi

