# Streamlit Cloud 배포 완료 가이드

## ✅ 준비 완료

프로젝트가 Streamlit Cloud 배포를 위해 준비되었습니다.

---

## 🚀 배포 단계

### 1단계: GitHub 저장소 생성 및 푸시

```bash
# 현재 디렉토리에서 실행
cd /Users/junyonglee/Documents/GitHub/whale_tracking

# GitHub 저장소 생성 (웹에서 또는 GitHub CLI 사용)
# 방법 1: GitHub 웹사이트에서
# 1. https://github.com/new 접속
# 2. Repository name: whale-arbitrage (또는 원하는 이름)
# 3. Public 또는 Private 선택
# 4. "Create repository" 클릭

# 방법 2: GitHub CLI 사용 (설치되어 있다면)
# gh repo create whale-arbitrage --public --source=. --remote=origin --push

# Git 원격 저장소 추가 및 푸시
git remote add origin https://github.com/YOUR_USERNAME/whale-arbitrage.git
git branch -M main
git push -u origin main
```

### 2단계: 데이터베이스 파일 처리

Streamlit Cloud는 임시 파일 시스템을 사용하므로 데이터베이스 파일을 별도로 처리해야 합니다.

#### 옵션 1: GitHub Releases에 업로드 (권장)

```bash
# 데이터베이스 파일 압축
tar -czf project.db.tar.gz data/project.db

# GitHub Releases에 업로드
# 1. https://github.com/YOUR_USERNAME/whale-arbitrage/releases/new 접속
# 2. Tag: v1.0.0
# 3. Release title: Initial Release
# 4. project.db.tar.gz 파일 드래그 앤 드롭
# 5. "Publish release" 클릭
```

그 후 `app/utils/data_loader.py`의 `_download_database_if_needed` 메서드가 자동으로 다운로드합니다.

#### 옵션 2: 외부 저장소 사용

Google Drive, Dropbox 등에 업로드하고 URL을 Secrets에 추가:
```
DATABASE_URL=https://your-storage.com/project.db
```

### 3단계: Streamlit Cloud에 배포

1. **Streamlit Cloud 접속**
   - https://share.streamlit.io/ 접속
   - 또는 https://streamlit.io/cloud

2. **GitHub로 로그인**
   - "Sign up" 또는 "Log in" 클릭
   - GitHub 계정으로 로그인

3. **앱 배포**
   - "New app" 버튼 클릭
   - 설정 입력:
     - **Repository**: `YOUR_USERNAME/whale-arbitrage`
     - **Branch**: `main`
     - **Main file path**: `app/main.py`
     - **App URL**: 원하는 URL (예: `whale-arbitrage`)

4. **Advanced settings 클릭**
   - **Python version**: `3.11`
   - **Secrets** 섹션에 다음 추가:
     ```toml
     ECOS_API_KEY = "your_ecos_api_key"
     UPBIT_API_KEY = "your_upbit_api_key"
     BINANCE_API_KEY = "your_binance_api_key"
     BITGET_API_KEY = "your_bitget_api_key"
     DATABASE_URL = "https://github.com/YOUR_USERNAME/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz"
     ```

5. **Deploy!** 클릭

### 4단계: 배포 확인

- 배포가 완료되면 `https://whale-arbitrage.streamlit.app` (또는 설정한 URL)로 접속
- 로그 확인: Streamlit Cloud 대시보드에서 "Manage app" → "Logs"

---

## 🔧 문제 해결

### 데이터베이스 파일을 찾을 수 없음

1. `DATABASE_URL`이 Secrets에 올바르게 설정되었는지 확인
2. GitHub Releases의 파일 URL이 올바른지 확인
3. 앱 로그에서 다운로드 오류 확인

### 환경 변수 오류

1. Streamlit Cloud 대시보드 → Settings → Secrets 확인
2. 코드에서 `st.secrets` 사용 확인

### Import 오류

1. `requirements.txt`에 모든 패키지가 포함되어 있는지 확인
2. 배포 로그에서 오류 메시지 확인

---

## 📝 참고 사항

- **자동 재배포**: GitHub에 푸시하면 자동으로 재배포됩니다
- **로그 확인**: Streamlit Cloud 대시보드에서 실시간 로그 확인 가능
- **환경 변수**: Secrets는 안전하게 암호화되어 저장됩니다

---

**작성일**: 2025-11-23

