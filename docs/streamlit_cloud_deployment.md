# Streamlit Cloud 배포 가이드

> **작성일**: 2025-11-23  
> **목적**: GitHub + Streamlit Cloud를 통한 무료 배포

---

## 🚀 Streamlit Cloud 배포 (가장 간단!)

Streamlit Cloud는 GitHub와 연동하여 **무료로** 서비스를 배포할 수 있는 플랫폼입니다.

---

## 📋 배포 전 준비

### 1. GitHub 저장소 준비
- 프로젝트를 GitHub에 푸시
- Public 또는 Private 저장소 모두 가능

### 2. 필수 파일 확인
- ✅ `requirements.txt` - Python 패키지 의존성
- ✅ `app/main.py` - Streamlit 앱 진입점
- ✅ `.streamlit/config.toml` - Streamlit 설정 (선택사항)

### 3. 환경 변수 준비
- `ECOS_API_KEY`: 한국은행 환율 API 키
- 기타 필요한 API 키들
- **Supabase (클라우드 DB 사용 시 필수)**:
  - `SUPABASE_URL`
  - `SUPABASE_KEY` (**권장: anon key / read-only 정책으로 운영**)
  - (수집/동기화 같은 관리자 작업용) `SUPABASE_SERVICE_ROLE_KEY` 는 **Streamlit 앱에는 넣지 말고** 로컬/CI에서만 사용 권장

---

## 🎯 배포 단계

### 1단계: GitHub에 코드 푸시

```bash
# Git 저장소 초기화 (아직 안했다면)
git init
git add .
git commit -m "Initial commit"

# GitHub 저장소 생성 후
git remote add origin https://github.com/yourusername/whale_tracking.git
git push -u origin main
```

### 2단계: Streamlit Cloud에 로그인

1. [Streamlit Cloud](https://streamlit.io/cloud) 접속
2. "Sign up" 또는 "Log in" 클릭
3. GitHub 계정으로 로그인

### 3단계: 앱 배포

1. Streamlit Cloud 대시보드에서 **"New app"** 클릭
2. 설정 입력:
   - **Repository**: `yourusername/whale_tracking`
   - **Branch**: `main` (또는 원하는 브랜치)
   - **Main file path**: `app/main.py`
   - **App URL**: 원하는 URL (예: `whale-arbitrage`)
3. **Advanced settings** 클릭:
   - **Python version**: 3.11
   - **Secrets**: 환경 변수 추가 (예시)
     ```
     ECOS_API_KEY=your_ecos_api_key
     UPBIT_API_KEY=your_upbit_api_key
     BINANCE_API_KEY=your_binance_api_key
     BITGET_API_KEY=your_bitget_api_key
     SUPABASE_URL=https://xxxx.supabase.co
     SUPABASE_KEY=your_supabase_anon_key
     ```
4. **Deploy!** 클릭

### 4단계: 데이터베이스 처리

Streamlit Cloud는 임시 파일 시스템을 사용하므로, 데이터베이스 파일을 직접 포함할 수 없습니다.

**해결 방법:**

#### 방법 1: GitHub Releases에 데이터베이스 업로드
```bash
# 데이터베이스 파일을 압축
tar -czf project.db.tar.gz data/project.db

# GitHub Releases에 업로드
# 또는 GitHub 저장소에 포함 (용량 제한 주의)
```

#### 방법 2: 앱 시작 시 데이터베이스 다운로드
`app/main.py`에 추가:
```python
import os
import urllib.request
from pathlib import Path

# 데이터베이스 파일이 없으면 다운로드
db_path = Path("data/project.db")
if not db_path.exists():
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # GitHub Releases 또는 다른 저장소에서 다운로드
    urllib.request.urlretrieve(
        "https://github.com/yourusername/whale_tracking/releases/download/v1.0/project.db",
        str(db_path)
    )
```

#### 방법 3: 외부 데이터베이스 사용
- Supabase (PostgreSQL)
- SQLite를 Supabase로 마이그레이션

> **권장 운영 방식 (이번 프로젝트 현재 상태)**  
> Streamlit Cloud에서는 `app/utils/data_loader.py`가 **Supabase 우선 연결**을 시도합니다.  
> 따라서 Streamlit Cloud Secrets에 `SUPABASE_URL`, `SUPABASE_KEY(anon)`만 설정하면, 앱이 항상 최신 Supabase 데이터를 사용합니다.

---

## ⚙️ 환경 변수 설정

Streamlit Cloud에서 환경 변수는 **Secrets**로 관리됩니다.

1. Streamlit Cloud 대시보드 → 앱 선택
2. **"⋮"** 메뉴 → **"Settings"**
3. **"Secrets"** 탭
4. 다음 형식으로 입력:
```toml
[secrets]
ECOS_API_KEY = "your_ecos_api_key"
UPBIT_API_KEY = "your_upbit_api_key"
BINANCE_API_KEY = "your_binance_api_key"
BITGET_API_KEY = "your_bitget_api_key"
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "your_supabase_anon_key"
```

코드에서 사용:
```python
import streamlit as st

ecos_api_key = st.secrets["ECOS_API_KEY"]
```

---

## 🔧 코드 수정 필요 사항

### 1. 환경 변수 읽기 방식 변경

`app/utils/data_loader.py` 등에서:
```python
# 기존
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("ECOS_API_KEY")

# Streamlit Cloud용
import streamlit as st
try:
    api_key = st.secrets["ECOS_API_KEY"]
except:
    # 로컬 개발용
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("ECOS_API_KEY")
```

### 2. 데이터베이스 경로 처리

`app/utils/data_loader.py`:
```python
import os
from pathlib import Path

# Streamlit Cloud에서는 /tmp 또는 현재 디렉토리 사용
if os.path.exists("/tmp"):
    DB_PATH = Path("/tmp") / "project.db"
else:
    ROOT = Path(__file__).resolve().parents[2]
    DB_PATH = ROOT / "data" / "project.db"
```

---

## 📝 Streamlit Cloud용 설정 파일

### `.streamlit/config.toml`
이미 생성되어 있습니다. Streamlit Cloud에서도 이 설정을 사용합니다.

### `requirements.txt`
Python 패키지 의존성이 명시되어 있어야 합니다.

---

## 🌐 배포 후 접속

배포가 완료되면:
- URL: `https://your-app-name.streamlit.app`
- 또는: `https://share.streamlit.io/yourusername/whale_tracking/main/app/main.py`

---

## 🔄 업데이트 배포

코드를 수정하고 GitHub에 푸시하면 자동으로 재배포됩니다:
```bash
git add .
git commit -m "Update app"
git push
```

---

## ⚠️ 제한 사항

1. **파일 시스템**: 임시 파일 시스템 사용 (재시작 시 삭제)
2. **용량 제한**: 저장소 크기 제한
3. **실행 시간**: 앱이 일정 시간 비활성화되면 자동으로 중지
4. **데이터베이스**: SQLite 파일을 직접 포함하기 어려움

---

## 🔒 보안

- 환경 변수는 Streamlit Cloud의 Secrets로 안전하게 관리
- Private 저장소도 지원
- HTTPS 자동 적용

---

## 📚 참고 자료

- [Streamlit Cloud 문서](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets 관리](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

