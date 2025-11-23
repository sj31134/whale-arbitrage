# Docker 배포 가이드

> **작성일**: 2025-11-23  
> **목적**: Streamlit 차익거래 분석 서비스를 Docker로 배포

---

## 📋 개요

이 가이드는 차익거래 분석 서비스를 Docker 컨테이너로 배포하여 외부에서 접속할 수 있게 하는 방법을 설명합니다.

---

## 🐳 Docker 파일 구조

```
whale_tracking/
├── Dockerfile              # Docker 이미지 빌드 파일
├── docker-compose.yml      # Docker Compose 설정
├── .dockerignore           # Docker 빌드 시 제외할 파일
├── scripts/
│   ├── docker_build.sh     # 이미지 빌드 스크립트
│   └── docker_deploy.sh    # 배포 스크립트
└── docs/
    └── docker_deployment_guide.md  # 이 문서
```

---

## 🚀 빠른 시작

### 방법 1: Docker Compose 사용 (권장)

```bash
# 1. 이미지 빌드 및 실행
docker-compose up -d --build

# 2. 로그 확인
docker-compose logs -f

# 3. 서비스 중지
docker-compose down
```

### 방법 2: Docker 직접 사용

```bash
# 1. 이미지 빌드
docker build -t arbitrage-ui:latest .

# 2. 컨테이너 실행
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config/.env:/app/config/.env:ro \
  --name arbitrage-ui \
  arbitrage-ui:latest

# 3. 로그 확인
docker logs -f arbitrage-ui

# 4. 컨테이너 중지
docker stop arbitrage-ui
docker rm arbitrage-ui
```

### 방법 3: 스크립트 사용

```bash
# 빌드
./scripts/docker_build.sh

# 배포
./scripts/docker_deploy.sh
```

---

## ⚙️ 설정

### 포트 설정

기본 포트: `8501`

다른 포트 사용 시:
```yaml
# docker-compose.yml
ports:
  - "8080:8501"  # 호스트:컨테이너
```

### 데이터 영속성

데이터베이스 파일은 볼륨으로 마운트되어 컨테이너 재시작 시에도 유지됩니다:

```yaml
volumes:
  - ./data:/app/data:rw
```

### 환경 변수

`.env` 파일은 자동으로 마운트됩니다:

```yaml
volumes:
  - ./config/.env:/app/config/.env:ro
```

필요한 환경 변수:
- `ECOS_API_KEY`: 한국은행 환율 API 키
- `UPBIT_API_KEY`: 업비트 API 키 (선택사항)
- `BINANCE_API_KEY`: 바이낸스 API 키 (선택사항)
- `BITGET_API_KEY`: 비트겟 API 키 (선택사항)

---

## 🌐 외부 접속

### 로컬 네트워크 접속

컨테이너 실행 후:
- 로컬: `http://localhost:8501`
- 같은 네트워크: `http://[서버IP]:8501`

### 인터넷 접속 (클라우드 배포)

#### AWS EC2
1. EC2 인스턴스 생성
2. 보안 그룹에서 포트 8501 열기
3. Docker 설치
4. 프로젝트 업로드
5. `docker-compose up -d` 실행
6. `http://[EC2_PUBLIC_IP]:8501` 접속

#### Google Cloud Platform
1. Compute Engine 인스턴스 생성
2. 방화벽 규칙에서 포트 8501 허용
3. Docker 설치
4. 프로젝트 업로드
5. `docker-compose up -d` 실행
6. `http://[GCP_EXTERNAL_IP]:8501` 접속

#### Azure
1. Virtual Machine 생성
2. Network Security Group에서 포트 8501 허용
3. Docker 설치
4. 프로젝트 업로드
5. `docker-compose up -d` 실행
6. `http://[AZURE_PUBLIC_IP]:8501` 접속

---

## 🔒 보안 고려사항

### 1. 방화벽 설정
- 필요한 포트만 열기
- SSH는 키 기반 인증 사용

### 2. HTTPS 설정 (프로덕션)
Nginx 리버스 프록시 사용:

```nginx
server {
    listen 80;
    server_name your-domain.com;

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

### 3. 인증 추가 (선택사항)
Streamlit의 기본 인증 기능 사용:

```python
# app/main.py
import streamlit as st

def check_password():
    """간단한 비밀번호 인증"""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("비밀번호가 올바르지 않습니다.")
        return False
    else:
        return True

if not check_password():
    st.stop()
```

---

## 📊 모니터링

### 로그 확인
```bash
# 실시간 로그
docker-compose logs -f

# 최근 100줄
docker-compose logs --tail=100
```

### 컨테이너 상태 확인
```bash
# 실행 중인 컨테이너
docker ps

# 모든 컨테이너
docker ps -a

# 리소스 사용량
docker stats arbitrage-ui
```

### 헬스체크
```bash
# 헬스체크 상태
docker inspect --format='{{.State.Health.Status}}' arbitrage-ui
```

---

## 🔧 트러블슈팅

### 포트가 이미 사용 중
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8501

# 다른 포트 사용
docker-compose.yml에서 포트 변경
```

### 데이터베이스 접근 오류
```bash
# 데이터 디렉토리 권한 확인
ls -la data/

# 권한 수정
chmod -R 755 data/
```

### 환경 변수 로드 실패
```bash
# .env 파일 확인
cat config/.env

# 컨테이너 내부 환경 변수 확인
docker exec arbitrage-ui env
```

---

## 📝 배포 체크리스트

- [ ] Docker 및 Docker Compose 설치 확인
- [ ] `data/project.db` 파일 존재 확인
- [ ] `config/.env` 파일 설정 확인
- [ ] 포트 8501 사용 가능 확인
- [ ] 방화벽 설정 (외부 접속 시)
- [ ] 이미지 빌드 성공 확인
- [ ] 컨테이너 실행 성공 확인
- [ ] 웹 브라우저에서 접속 확인

---

## 🚀 프로덕션 배포 예시

### 1. 서버 준비
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 프로젝트 업로드
```bash
# Git 사용
git clone <repository-url>
cd whale_tracking

# 또는 SCP 사용
scp -r whale_tracking user@server:/path/to/
```

### 3. 배포 실행
```bash
cd whale_tracking
./scripts/docker_deploy.sh
```

### 4. 접속 확인
```bash
curl http://localhost:8501/_stcore/health
```

---

## 📚 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [Streamlit 배포 가이드](https://docs.streamlit.io/deploy)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

