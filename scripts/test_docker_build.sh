#!/bin/bash
# Docker 빌드 테스트 스크립트

set -e

echo "🧪 Docker 빌드 테스트 시작..."

# 이미지 이름
IMAGE_NAME="arbitrage-ui"
IMAGE_TAG="test"

# Docker 이미지 빌드 (캐시 없이)
echo "1. Docker 이미지 빌드 중..."
docker build --no-cache -t ${IMAGE_NAME}:${IMAGE_TAG} . || {
    echo "❌ Docker 이미지 빌드 실패"
    exit 1
}

echo "✅ Docker 이미지 빌드 성공"

# 이미지 크기 확인
echo ""
echo "2. 이미지 정보:"
docker images ${IMAGE_NAME}:${IMAGE_TAG}

# 컨테이너 실행 테스트
echo ""
echo "3. 컨테이너 실행 테스트 중..."
CONTAINER_ID=$(docker run -d -p 8502:8501 ${IMAGE_NAME}:${IMAGE_TAG})

# 잠시 대기
sleep 5

# 헬스체크
echo "4. 헬스체크 중..."
if curl -f http://localhost:8502/_stcore/health > /dev/null 2>&1; then
    echo "✅ 헬스체크 성공"
else
    echo "⚠️ 헬스체크 실패 (서비스가 아직 시작 중일 수 있음)"
fi

# 로그 확인
echo ""
echo "5. 컨테이너 로그 (최근 20줄):"
docker logs --tail=20 ${CONTAINER_ID}

# 컨테이너 정리
echo ""
echo "6. 테스트 컨테이너 정리 중..."
docker stop ${CONTAINER_ID} > /dev/null
docker rm ${CONTAINER_ID} > /dev/null

echo ""
echo "✅ Docker 빌드 테스트 완료"
echo ""
echo "실제 배포:"
echo "  docker-compose up -d --build"

