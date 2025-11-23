# 외부 접속 배포 가이드

> **작성일**: 2025-11-23  
> **목적**: 차익거래 분석 서비스를 외부에서 접속 가능하도록 배포

---

## 📋 개요

이 가이드는 서비스를 클라우드 서버에 배포하여 인터넷을 통해 접속할 수 있게 하는 방법을 설명합니다.

---

## 🚀 빠른 배포 (자동 스크립트)

### 1. 서버 준비
- 클라우드 서버 (AWS EC2, GCP, Azure 등)
- SSH 접속 가능
- 포트 8501 열기 (방화벽 설정)

### 2. 자동 배포 스크립트 실행
```bash
# 배포 스크립트 실행
./scripts/deploy_to_server.sh [서버IP] [사용자명]

# 예시
./scripts/deploy_to_server.sh 123.456.789.0 ubuntu
```

---

## 📝 수동 배포 방법

### 1단계: 서버 준비

#### Docker 설치
```bash
# 서버에 SSH 접속
ssh user@server

# Docker 설치 스크립트 실행
bash <(curl -fsSL https://get.docker.com)
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

또는 로컬에서:
```bash
ssh user@server 'bash -s' < scripts/install_docker_on_server.sh
```

### 2단계: 프로젝트 업로드

#### 방법 1: Git 사용 (권장)
```bash
# 서버에서
cd ~
git clone <repository-url>
cd whale_tracking
```

#### 방법 2: rsync 사용
```bash
# 로컬에서
rsync -avz --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    ./ user@server:~/whale_tracking/
```

#### 방법 3: SCP 사용
```bash
# 로컬에서
scp -r whale_tracking user@server:~/
```

### 3단계: 환경 설정

#### 환경 변수 파일 생성
```bash
# 서버에서
cd ~/whale_tracking
mkdir -p config
nano config/.env
```

`.env` 파일 내용:
```
ECOS_API_KEY=your_ecos_api_key
UPBIT_API_KEY=your_upbit_api_key
BINANCE_API_KEY=your_binance_api_key
BITGET_API_KEY=your_bitget_api_key
```

#### 데이터베이스 파일 복사
```bash
# 로컬에서
scp data/project.db user@server:~/whale_tracking/data/
```

### 4단계: 방화벽 설정

#### AWS EC2
1. EC2 콘솔 → Security Groups
2. 인바운드 규칙 추가:
   - Type: Custom TCP
   - Port: 8501
   - Source: 0.0.0.0/0 (또는 특정 IP)

#### GCP
```bash
# 방화벽 규칙 생성
gcloud compute firewall-rules create allow-streamlit \
    --allow tcp:8501 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow Streamlit access"
```

#### Azure
1. Azure Portal → Network Security Group
2. 인바운드 보안 규칙 추가:
   - Destination port ranges: 8501
   - Source: Any

#### Ubuntu (UFW)
```bash
sudo ufw allow 8501/tcp
sudo ufw reload
```

### 5단계: 배포 실행

```bash
# 서버에서
cd ~/whale_tracking
docker-compose -f docker-compose.prod.yml up -d --build
```

### 6단계: 접속 확인

```bash
# 서버에서 확인
curl http://localhost:8501/_stcore/health

# 외부에서 접속
# 브라우저에서: http://[서버IP]:8501
```

---

## 🔒 보안 강화 (선택사항)

### 1. Nginx 리버스 프록시 + HTTPS

#### Nginx 설치
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

#### Nginx 설정
```bash
sudo nano /etc/nginx/sites-available/arbitrage
```

설정 내용:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 또는 서버 IP

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 설정 활성화
```bash
sudo ln -s /etc/nginx/sites-available/arbitrage /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### HTTPS 설정 (Let's Encrypt)
```bash
sudo certbot --nginx -d your-domain.com
```

### 2. 인증 추가

Streamlit의 기본 인증 기능을 사용하거나, Nginx에서 Basic Auth를 설정할 수 있습니다.

---

## 📊 모니터링 및 관리

### 로그 확인
```bash
# 실시간 로그
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml logs -f'

# 최근 100줄
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml logs --tail=100'
```

### 컨테이너 재시작
```bash
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml restart'
```

### 컨테이너 중지
```bash
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml down'
```

### 업데이트 배포
```bash
# 코드 업데이트 후
ssh user@server 'cd ~/whale_tracking && git pull && docker-compose -f docker-compose.prod.yml up -d --build'
```

---

## 🌐 클라우드별 배포 가이드

### AWS EC2
1. EC2 인스턴스 생성 (Ubuntu 22.04 LTS 권장)
2. 보안 그룹에서 포트 22(SSH), 8501(Streamlit) 열기
3. Elastic IP 할당 (선택사항)
4. 위의 "수동 배포 방법" 따라하기

### Google Cloud Platform
1. Compute Engine 인스턴스 생성
2. 방화벽 규칙에서 포트 8501 허용
3. 외부 IP 할당
4. 위의 "수동 배포 방법" 따라하기

### Azure
1. Virtual Machine 생성
2. Network Security Group에서 포트 8501 허용
3. Public IP 할당
4. 위의 "수동 배포 방법" 따라하기

---

## 🔧 트러블슈팅

### 포트가 열려있지 않음
```bash
# 방화벽 확인
sudo ufw status
sudo netstat -tuln | grep 8501
```

### 컨테이너가 시작되지 않음
```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml logs

# 컨테이너 상태 확인
docker ps -a
```

### 외부에서 접속 불가
1. 방화벽 설정 확인
2. 보안 그룹/방화벽 규칙 확인
3. 서버에서 `curl http://localhost:8501` 테스트
4. 서버 IP가 올바른지 확인

---

## ✅ 배포 체크리스트

- [ ] 서버에 Docker 설치
- [ ] 프로젝트 파일 업로드
- [ ] `.env` 파일 설정
- [ ] `data/project.db` 파일 복사
- [ ] 방화벽에서 포트 8501 열기
- [ ] Docker Compose로 배포
- [ ] 로컬에서 접속 확인 (`curl http://localhost:8501`)
- [ ] 외부에서 접속 확인 (`http://[서버IP]:8501`)
- [ ] (선택) HTTPS 설정
- [ ] (선택) 도메인 연결

---

## 📚 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [Streamlit 배포 가이드](https://docs.streamlit.io/deploy)
- [Nginx 리버스 프록시 설정](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

