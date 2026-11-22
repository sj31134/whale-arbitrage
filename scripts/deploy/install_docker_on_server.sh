#!/bin/bash
# 서버에 Docker 설치 스크립트
# 사용법: ssh user@server 'bash -s' < scripts/deploy/install_docker_on_server.sh

set -e

echo "🐳 Docker 설치 시작..."

# Docker 설치
if ! command -v docker &> /dev/null; then
    echo "Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker 설치 완료"
else
    echo "✅ Docker가 이미 설치되어 있습니다: $(docker --version)"
fi

# Docker Compose 설치
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose 설치 중..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 설치 완료"
else
    echo "✅ Docker Compose가 이미 설치되어 있습니다: $(docker-compose --version)"
fi

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# Docker 서비스 시작 및 자동 시작 설정
sudo systemctl enable docker
sudo systemctl start docker

echo ""
echo "✅ Docker 설치 완료!"
echo ""
echo "⚠️  중요: SSH 세션을 다시 시작하거나 다음 명령어를 실행하세요:"
echo "   newgrp docker"
echo ""
echo "설치 확인:"
echo "   docker --version"
echo "   docker-compose --version"

