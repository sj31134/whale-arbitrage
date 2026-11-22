#!/bin/bash
# Docker 이미지 빌드 스크립트

set -e

echo "🐳 Docker 이미지 빌드 시작..."

# 이미지 이름
IMAGE_NAME="arbitrage-ui"
IMAGE_TAG="latest"

# Docker 이미지 빌드
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "✅ Docker 이미지 빌드 완료: ${IMAGE_NAME}:${IMAGE_TAG}"

# 이미지 확인
echo ""
echo "📦 빌드된 이미지:"
docker images | grep ${IMAGE_NAME}

echo ""
echo "🚀 실행 방법:"
echo "  docker run -d -p 8501:8501 -v \$(pwd)/data:/app/data ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "또는 docker-compose 사용:"
echo "  docker-compose up -d"

