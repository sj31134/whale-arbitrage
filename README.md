# Whale Tracking 프로젝트

고래(Whale) 지갑의 거래 데이터를 수집하고 분석하는 프로젝트입니다.

## 🚀 빠른 시작

### 로컬에서 앱 실행 (localhost)
```bash
cd whale_tracking
source venv/bin/activate   # Windows: venv\Scripts\activate
# 리스크 예측·고래 데이터를 로컬 DB(SQLite)만 사용하려면:
export USE_LOCAL_DB=1     # 또는 config/.env에 USE_LOCAL_DB=1 추가
streamlit run app/main.py
```
**접속 주소:** **http://localhost:8501**  
(포트는 `.streamlit/config.toml`에서 `port = 8501`로 설정됨)

### 데이터 수집
```bash
# 병렬 수집 실행
python3 scripts/main/run_parallel_collection.py

# 개별 수집
python3 scripts/collectors/collect_btc_whale_transactions.py
python3 scripts/collectors/collect_price_history_hourly.py
```

### 데이터 분석
```bash
python3 scripts/analysis/analyze_top_picks.py
```

### 유지보수
```bash
# 라벨 업데이트
python3 scripts/maintenance/update_labels_stable.py

# Transaction Direction 업데이트
python3 scripts/maintenance/update_direction_direct.py
```

## 📁 프로젝트 구조

자세한 구조는 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)를 참조하세요.

### 핵심 디렉토리
- `scripts/collectors/` - 기존 Supabase 중심 수집 스크립트
- `scripts/subprojects/` - Arbitrage & Risk AI 전용 수집/분석 템플릿
- `scripts/maintenance/` - 데이터베이스/라벨 관리 도구
- `scripts/main/` - 통합 실행 스크립트
- `data/` - 수집한 과거 데이터 + SQLite(`project.db`)
- `docs/` - 가이드 및 구조 문서

# 📌 서브 프로젝트 시작

Project 2/3 서브 프로젝트는 `docs/guides/subproject_data_pipeline.md`를 참고하세요.  
`scripts/maintenance/init_subproject_db.py`를 실행하여 `data/project.db` 구조를 만든 후 다음을 실행하면 됩니다:

```bash
python3 scripts/subprojects/arbitrage/fetch_spot_quotes.py
python3 scripts/subprojects/risk_ai/fetch_futures_metrics.py
python3 scripts/subprojects/risk_ai/fetch_bitinfo_whale.py
```

## 📋 요구사항

```bash
pip install -r requirements.txt
```

## ⚙️ 설정

`config/.env` 파일에 Supabase 설정을 추가하세요:
```
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key
```

## 🐳 배포 방법

차익거래 분석 서비스를 배포하는 여러 방법:

### 방법 1: Streamlit Cloud (가장 간단! 무료!)
GitHub에 푸시하고 Streamlit Cloud에서 배포
- [README_STREAMLIT_CLOUD.md](./README_STREAMLIT_CLOUD.md)
- [docs/streamlit_cloud_deployment.md](./docs/streamlit_cloud_deployment.md)

### 방법 2: Docker + ngrok (로컬에서 외부 접속)
로컬 Docker 컨테이너를 ngrok으로 외부 접속 가능하게
- [README_NGROK.md](./README_NGROK.md)
- [docs/docker_ngrok_deployment.md](./docs/docker_ngrok_deployment.md)

### 방법 3: 로컬 Docker
```bash
docker-compose up -d --build
# 접속: http://localhost:8501
```
- [README_DOCKER.md](./README_DOCKER.md)

### 방법 4: 클라우드 서버 배포
```bash
./scripts/deploy_to_server.sh [서버IP] [사용자명]
```
- [README_DEPLOY.md](./README_DEPLOY.md)

## 📚 문서

- [프로젝트 구조 가이드](./PROJECT_STRUCTURE.md)
- [API 키 발급 가이드](./docs/guides/API_키_발급_가이드.md)
- [Docker 배포 가이드](./docs/docker_deployment_guide.md)

