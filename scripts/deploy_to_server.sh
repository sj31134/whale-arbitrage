#!/bin/bash
# 서버 배포 스크립트
# 사용법: ./scripts/deploy_to_server.sh [서버IP] [사용자명]

set -e

SERVER_IP=${1:-""}
SERVER_USER=${2:-"ubuntu"}

if [ -z "$SERVER_IP" ]; then
    echo "❌ 사용법: $0 [서버IP] [사용자명]"
    echo "예시: $0 123.456.789.0 ubuntu"
    exit 1
fi

echo "🚀 서버 배포 시작..."
echo "서버: $SERVER_USER@$SERVER_IP"

# 1. 서버 연결 확인
echo ""
echo "1. 서버 연결 확인 중..."
ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_IP "echo '✅ 서버 연결 성공'" || {
    echo "❌ 서버에 연결할 수 없습니다."
    echo "   - SSH 키가 설정되어 있는지 확인하세요."
    echo "   - 방화벽에서 SSH 포트(22)가 열려있는지 확인하세요."
    exit 1
}

# 2. Docker 설치 확인
echo ""
echo "2. Docker 설치 확인 중..."
ssh $SERVER_USER@$SERVER_IP "docker --version" || {
    echo "⚠️ Docker가 설치되어 있지 않습니다."
    echo "   Docker 설치 스크립트를 실행하시겠습니까? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Docker 설치 중..."
        ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            sudo systemctl enable docker
            sudo systemctl start docker
            echo "✅ Docker 설치 완료"
ENDSSH
    else
        echo "❌ Docker가 필요합니다. 설치 후 다시 시도하세요."
        exit 1
    fi
}

# 3. 프로젝트 디렉토리 생성
echo ""
echo "3. 서버에 프로젝트 디렉토리 생성 중..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p ~/whale_tracking"

# 4. 필요한 파일만 전송 (rsync 사용)
echo ""
echo "4. 프로젝트 파일 전송 중..."
rsync -avz --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'data/*.db' \
    --exclude 'data/*.db-shm' \
    --exclude 'data/*.db-wal' \
    ./ $SERVER_USER@$SERVER_IP:~/whale_tracking/

# 5. .env 파일 확인 및 안내
echo ""
echo "5. 환경 변수 파일 확인 중..."
ssh $SERVER_USER@$SERVER_IP "test -f ~/whale_tracking/config/.env" || {
    echo "⚠️ config/.env 파일이 없습니다."
    echo "   서버에 config/.env 파일을 생성해야 합니다."
    echo "   다음 명령어로 생성하세요:"
    echo "   ssh $SERVER_USER@$SERVER_IP 'mkdir -p ~/whale_tracking/config && nano ~/whale_tracking/config/.env'"
}

# 6. 데이터베이스 파일 확인
echo ""
echo "6. 데이터베이스 파일 확인 중..."
ssh $SERVER_USER@$SERVER_IP "test -f ~/whale_tracking/data/project.db" || {
    echo "⚠️ data/project.db 파일이 없습니다."
    echo "   데이터베이스 파일을 서버에 복사해야 합니다."
    echo "   다음 명령어로 복사하세요:"
    echo "   scp data/project.db $SERVER_USER@$SERVER_IP:~/whale_tracking/data/"
}

# 7. Docker Compose로 배포
echo ""
echo "7. Docker Compose로 배포 중..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH
    cd ~/whale_tracking
    docker-compose -f docker-compose.prod.yml down || true
    docker-compose -f docker-compose.prod.yml up -d --build
ENDSSH

# 8. 배포 확인
echo ""
echo "8. 배포 확인 중..."
sleep 5
ssh $SERVER_USER@$SERVER_IP "docker ps | grep arbitrage-ui" || {
    echo "⚠️ 컨테이너가 실행되지 않았습니다."
    echo "   로그를 확인하세요:"
    echo "   ssh $SERVER_USER@$SERVER_IP 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml logs'"
    exit 1
}

echo ""
echo "✅ 배포 완료!"
echo ""
echo "🌐 접속 정보:"
echo "   URL: http://$SERVER_IP:8501"
echo ""
echo "📋 유용한 명령어:"
echo "   로그 확인: ssh $SERVER_USER@$SERVER_IP 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml logs -f'"
echo "   컨테이너 재시작: ssh $SERVER_USER@$SERVER_IP 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml restart'"
echo "   컨테이너 중지: ssh $SERVER_USER@$SERVER_IP 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml down'"
echo ""
echo "🔒 보안 설정:"
echo "   - 방화벽에서 포트 8501이 열려있는지 확인하세요."
echo "   - HTTPS 설정을 권장합니다 (Nginx 리버스 프록시 사용)."

