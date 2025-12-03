# Docker + ngrok 배포 가이드

## 🚀 로컬에서 외부 접속 가능하게 만들기

ngrok을 사용하면 로컬 Docker 컨테이너를 인터넷을 통해 접속할 수 있습니다.

---

## 📋 준비

1. ngrok 설치: https://ngrok.com/download
2. ngrok 계정 생성 및 인증 토큰 받기

---

## 🎯 사용 방법

### 1. ngrok 인증
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 2. Docker 컨테이너 실행
```bash
docker-compose up -d
```

### 3. ngrok 터널 생성
```bash
ngrok http 8501
```

또는 자동 스크립트:
```bash
./scripts/run_with_ngrok.sh
```

---

## 🌐 접속

ngrok이 제공하는 URL로 접속:
- 예: `https://abc123.ngrok-free.app`

---

## ⚠️ 제한사항

- 무료 플랜: 세션 시간 제한, 랜덤 URL
- 로컬 머신이 켜져 있어야 함

---

## 📚 자세한 가이드

[docs/docker_ngrok_deployment.md](docs/docker_ngrok_deployment.md)를 참조하세요.

