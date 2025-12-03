# Docker + ngrok 배포 가이드

> **작성일**: 2025-11-23  
> **목적**: 로컬 Docker 컨테이너를 ngrok으로 외부 접속 가능하게 만들기

---

## 🚀 ngrok을 사용한 로컬 배포

ngrok을 사용하면 로컬에서 실행 중인 Docker 컨테이너를 인터넷을 통해 접속할 수 있게 할 수 있습니다.

---

## 📋 준비 사항

1. Docker 및 Docker Compose 설치
2. ngrok 계정 및 설치
3. ngrok 인증 토큰

---

## 🎯 배포 단계

### 1단계: ngrok 설치

#### macOS
```bash
brew install ngrok/ngrok/ngrok
```

#### Linux
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
    sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
    sudo tee /etc/apt/sources.list.d/ngrok.list && \
    sudo apt update && sudo apt install ngrok
```

#### Windows
[ngrok 다운로드](https://ngrok.com/download)

### 2단계: ngrok 인증

1. [ngrok.com](https://ngrok.com)에서 계정 생성
2. 인증 토큰 받기
3. 로컬에서 인증:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 3단계: Docker 컨테이너 실행

```bash
cd whale_tracking
docker-compose up -d
```

### 4단계: ngrok 터널 생성

```bash
ngrok http 8501
```

출력 예시:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8501
```

이제 `https://abc123.ngrok-free.app`로 접속할 수 있습니다!

---

## 🔧 자동화 스크립트

### `scripts/run_with_ngrok.sh`
```bash
#!/bin/bash
# Docker + ngrok 자동 실행 스크립트

set -e

echo "🚀 Docker 컨테이너 시작 중..."
docker-compose up -d

echo "⏳ 컨테이너 시작 대기 중..."
sleep 5

echo "🌐 ngrok 터널 생성 중..."
echo "접속 URL이 표시됩니다:"
ngrok http 8501
```

사용:
```bash
chmod +x scripts/run_with_ngrok.sh
./scripts/run_with_ngrok.sh
```

---

## ⚙️ ngrok 고급 설정

### 고정 도메인 사용 (유료)

```bash
ngrok http 8501 --domain=your-domain.ngrok-free.app
```

### 설정 파일 사용

`ngrok.yml`:
```yaml
version: "2"
authtoken: YOUR_AUTH_TOKEN
tunnels:
  streamlit:
    addr: 8501
    proto: http
    domain: your-domain.ngrok-free.app  # 유료 플랜 필요
```

실행:
```bash
ngrok start streamlit
```

---

## 🔒 보안 고려사항

1. **무료 플랜 제한**:
   - 세션 시간 제한
   - 랜덤 URL (매번 변경)
   - 연결 수 제한

2. **보안**:
   - ngrok은 기본적으로 공개 접속 가능
   - 인증을 추가하려면 ngrok의 인증 기능 사용

3. **인증 추가**:
```bash
ngrok http 8501 --basic-auth="username:password"
```

---

## 📊 모니터링

ngrok 웹 인터페이스:
- http://localhost:4040 (로컬)
- https://dashboard.ngrok.com (온라인)

---

## ⚠️ 제한 사항

1. **무료 플랜**:
   - 세션 시간 제한
   - 랜덤 URL
   - 연결 수 제한

2. **로컬 머신 필요**:
   - 로컬 머신이 켜져 있어야 함
   - 인터넷 연결 필요

---

## 🔄 대안

### Cloudflare Tunnel (무료, 더 안정적)

```bash
# Cloudflare Tunnel 설치
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# 터널 생성
cloudflared tunnel create whale-tracking

# 실행
cloudflared tunnel run whale-tracking
```

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

