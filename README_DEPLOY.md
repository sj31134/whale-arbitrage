# 외부 접속 배포 가이드

## 🚀 빠른 시작

### 자동 배포 (권장)
```bash
./scripts/deploy_to_server.sh [서버IP] [사용자명]
```

예시:
```bash
./scripts/deploy_to_server.sh 123.456.789.0 ubuntu
```

---

## 📋 필수 사항

1. **클라우드 서버** (AWS EC2, GCP, Azure 등)
2. **SSH 접속 가능**
3. **방화벽에서 포트 8501 열기**

---

## 🔧 수동 배포

### 1. 서버에 Docker 설치
```bash
ssh user@server 'bash -s' < scripts/install_docker_on_server.sh
```

### 2. 프로젝트 업로드
```bash
rsync -avz --exclude '.git' ./ user@server:~/whale_tracking/
```

### 3. 환경 설정
```bash
# 서버에서
cd ~/whale_tracking
mkdir -p config
nano config/.env  # API 키 설정
```

### 4. 데이터베이스 복사
```bash
scp data/project.db user@server:~/whale_tracking/data/
```

### 5. 배포 실행
```bash
# 서버에서
cd ~/whale_tracking
docker-compose -f docker-compose.prod.yml up -d --build
```

### 6. 접속
- `http://[서버IP]:8501`

---

## 🔒 보안 설정

### 방화벽 설정
- AWS EC2: Security Group에서 포트 8501 허용
- GCP: 방화벽 규칙에서 포트 8501 허용
- Azure: Network Security Group에서 포트 8501 허용

### HTTPS 설정 (선택사항)
Nginx 리버스 프록시 + Let's Encrypt 사용

---

## 📚 자세한 가이드

자세한 내용은 [docs/deploy_external_access_guide.md](docs/deploy_external_access_guide.md)를 참조하세요.

