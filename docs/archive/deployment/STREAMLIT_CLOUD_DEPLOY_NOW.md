# 🚀 Streamlit Cloud 배포 바로 시작!

## ✅ 완료된 작업

- [x] GitHub 저장소 생성: https://github.com/sj31134/whale-arbitrage
- [x] 코드 푸시 완료
- [x] 데이터베이스 파일 압축 완료

## 🎯 지금 바로 Streamlit Cloud 배포하기

### 1단계: Streamlit Cloud 접속
https://share.streamlit.io/ 접속

### 2단계: GitHub로 로그인
- "Sign up" 또는 "Log in" 클릭
- GitHub 계정으로 로그인

### 3단계: 앱 배포
1. **"New app"** 버튼 클릭
2. 설정 입력:
   - **Repository**: `sj31134/whale-arbitrage`
   - **Branch**: `main`
   - **Main file path**: `app/main.py`
   - **App URL**: `whale-arbitrage` (또는 원하는 이름)

### 4단계: Secrets 설정
**Advanced settings** 클릭 → **Secrets** 섹션에 다음 추가:

```toml
ECOS_API_KEY = "your_ecos_api_key"
DATABASE_URL = "https://github.com/sj31134/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz"
```

### 5단계: Deploy!
**"Deploy!"** 버튼 클릭

## 📊 배포 후

- 배포 완료 후: `https://whale-arbitrage.streamlit.app` 접속
- 로그 확인: Streamlit Cloud 대시보드 → "Manage app" → "Logs"

## 🔧 문제 해결

### 데이터베이스 오류
- Secrets의 `DATABASE_URL` 확인
- GitHub Releases에서 파일 다운로드 가능한지 확인

### 환경 변수 오류
- Secrets 설정 확인
- `ECOS_API_KEY`가 올바른지 확인

---

**작성일**: 2025-11-23

