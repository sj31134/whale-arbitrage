# Streamlit Cloud 배포 상태 확인

## 📊 현재 상태

### 1. 데이터 수집 완료 여부

✅ **완료**
- **ETHUSDT 데이터**: 2022-01-01 ~ 2025-11-30
  - `binance_futures_metrics`: 1,430건 (펀딩비, OI)
  - `futures_extended_metrics`: 1,304건 (Top Trader, Taker 비율)
- **BTCUSDT 데이터**: 2022-01-01 ~ 2025-11-30
  - `binance_futures_metrics`: 1,428건
  - `futures_extended_metrics`: 1,304건
- **DB 파일 크기**: 2.34 MB
- **최종 수정 시간**: 2025-11-30 17:56:47

### 2. Streamlit Cloud 데이터베이스 설정

#### 현재 설정 (app/utils/data_loader.py)

```python
# Streamlit Cloud 환경 감지
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
    DB_PATH = Path('/tmp') / "project.db"
    USE_SUPABASE = True  # 클라우드에서는 Supabase 우선 사용
```

**동작 방식:**
1. **우선순위 1: Supabase** (USE_SUPABASE = True)
   - Streamlit Cloud Secrets에서 `SUPABASE_URL`, `SUPABASE_KEY` 읽기
   - Supabase 연결 성공 시 SQLite 파일 불필요
   - 모든 데이터를 Supabase에서 직접 조회

2. **폴백: SQLite** (Supabase 연결 실패 시)
   - `DATABASE_URL` Secret에서 `.tar.gz` 파일 다운로드
   - `/tmp/project.db`에 압축 해제
   - 로컬 SQLite 파일 사용

#### Supabase 동기화 상태

✅ **완료**
- `binance_futures_metrics`: 2,858건 (BTC + ETH)
- `futures_extended_metrics`: 2,608건 (BTC + ETH)
- `bitinfocharts_whale`: 1,068건 (이미 존재)

**결론**: Streamlit Cloud는 **Supabase를 우선 사용**하며, Supabase에 최신 데이터가 동기화되어 있으므로 **SQLite 파일은 폴백용**입니다.

### 3. project.db.tar.gz 파일 상태

#### 현재 상태
- **파일 위치**: `/Users/junyonglee/Documents/GitHub/whale_tracking/project.db.tar.gz`
- **파일 크기**: 561 KB (이전 버전, 11월 27일 생성)
- **최신 버전**: 2.34 MB (11월 30일 17:56 생성)

#### 업데이트 필요
- ✅ 최신 `data/project.db`로 `project.db.tar.gz` 재생성 완료
- ⏳ GitHub에 푸시 필요
- ⏳ Streamlit Cloud Secret 확인 필요

---

## 🔧 해야 할 작업

### 1. GitHub에 최신 파일 푸시

```bash
# 최신 project.db.tar.gz 생성 (완료)
tar -czf project.db.tar.gz -C data project.db

# Git에 추가 및 커밋
git add project.db.tar.gz
git commit -m "chore: 최신 ETH 데이터 포함 project.db.tar.gz 업데이트"
git push origin main
```

### 2. Streamlit Cloud Secret 확인

Streamlit Cloud 대시보드 → 앱 선택 → Settings → Secrets에서 다음이 설정되어 있어야 합니다:

#### 필수 Secret (Supabase 사용 시)
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

#### 선택적 Secret (Supabase 폴백용)
```toml
DATABASE_URL = "https://github.com/YOUR_USERNAME/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz"
```

**참고**: Supabase가 정상 작동하면 `DATABASE_URL`은 필요 없습니다.

### 3. GitHub Releases 업데이트 (선택 사항)

Supabase를 사용하지 않는 경우를 대비해 GitHub Releases에도 업데이트:

1. https://github.com/YOUR_USERNAME/whale-arbitrage/releases 접속
2. 최신 Release 선택 또는 새 Release 생성
3. `project.db.tar.gz` 파일 업로드
4. 다운로드 URL을 `DATABASE_URL` Secret에 설정

---

## ✅ 확인 체크리스트

- [x] 데이터 수집 완료 (ETHUSDT 2025-11-30까지)
- [x] Supabase 동기화 완료 (binance_futures_metrics, futures_extended_metrics)
- [x] project.db.tar.gz 최신 버전 생성
- [ ] GitHub에 project.db.tar.gz 푸시
- [ ] Streamlit Cloud Secret 확인 (SUPABASE_URL, SUPABASE_KEY)
- [ ] Streamlit Cloud 앱 재배포 (필요 시)

---

## 📝 참고

### Streamlit Cloud 데이터 소스 우선순위

1. **Supabase** (USE_SUPABASE = True)
   - Streamlit Cloud Secrets에서 `SUPABASE_URL`, `SUPABASE_KEY` 읽기
   - 모든 데이터를 Supabase에서 직접 조회
   - ✅ **현재 권장 방식** (최신 데이터 보장)

2. **SQLite 파일** (Supabase 폴백)
   - `DATABASE_URL` Secret에서 `.tar.gz` 파일 다운로드
   - `/tmp/project.db`에 압축 해제
   - 로컬 SQLite 파일 사용
   - ⚠️ 파일이 오래되면 최신 데이터 누락 가능

### 권장 설정

**Streamlit Cloud Secret:**
```toml
# 필수 (Supabase 사용)
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-service-role-key"

# 선택적 (Supabase 폴백용)
DATABASE_URL = "https://github.com/YOUR_USERNAME/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz"
```

**결론**: Supabase에 최신 데이터가 동기화되어 있으므로, **Supabase를 우선 사용**하는 것이 권장됩니다. SQLite 파일은 Supabase 연결 실패 시에만 사용됩니다.

