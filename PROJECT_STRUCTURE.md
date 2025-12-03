# 프로젝트 구조 가이드

> **최종 업데이트**: 2025-11-30  
> 프로젝트 파일들을 논리적으로 분류하여 구조화했습니다.

## 📁 전체 디렉토리 구조

```
whale_tracking/
├── app/                          # Streamlit 웹 애플리케이션
│   ├── main.py                  # 메인 앱 진입점
│   ├── pages/                   # 페이지 모듈
│   │   ├── cost_calculator_page.py
│   │   ├── strategy_recommender_page.py
│   │   ├── risk_dashboard_page.py
│   │   ├── historical_analysis_page.py
│   │   ├── feature_analysis_page.py
│   │   ├── derivatives_analysis_page.py
│   │   ├── dynamic_variables_page.py
│   │   ├── model_comparison_page.py
│   │   ├── comprehensive_dashboard_page.py
│   │   └── trading_bot_page.py
│   └── utils/                   # 유틸리티 모듈
│       ├── data_loader.py       # 데이터 로더
│       ├── calculator.py        # 비용 계산기
│       ├── recommender.py       # 전략 추천
│       ├── visualizer.py        # 차트 생성
│       ├── risk_predictor.py    # 리스크 예측
│       ├── risk_analyzer.py     # 리스크 분석
│       ├── feature_explainer.py # 특성 설명
│       └── secrets_helper.py    # Secrets 관리
│
├── config/                      # 설정 파일
│   └── .env                     # 환경 변수 (Git 제외)
│
├── data/                        # 데이터 파일
│   ├── project.db              # SQLite 데이터베이스
│   ├── models/                 # 학습된 모델 파일
│   ├── analysis/               # 분석 결과 CSV
│   ├── exports/                # 내보낸 파일
│   └── richlist/               # Rich List CSV
│
├── docs/                        # 문서
│   ├── deployment/             # 배포 관련 문서
│   ├── guides/                 # 사용 가이드
│   ├── reports/                # 프로젝트 보고서
│   ├── analysis/               # 데이터 분석 문서
│   └── README.md               # 문서 인덱스
│
├── logs/                        # 로그 파일 (Git 제외)
│
├── scripts/                     # Python 스크립트
│   ├── collectors/             # 데이터 수집 스크립트
│   ├── analysis/               # 데이터 분석 스크립트
│   ├── maintenance/           # 유지보수 스크립트
│   ├── main/                  # 메인 실행 스크립트
│   └── subprojects/            # 서브 프로젝트
│       ├── arbitrage/         # Project 2: 차익거래
│       └── risk_ai/           # Project 3: 리스크 AI
│
├── sql/                         # SQL 파일
│   ├── create_project_tables.sql
│   └── migrations/            # 마이그레이션 SQL
│
├── src/                         # 소스 코드 모듈
│   ├── collectors/            # 수집 모듈
│   └── utils/                 # 유틸리티 모듈
│
├── temp/                        # 임시 파일 (Git 제외)
│
├── tests/                       # 테스트 코드
│   ├── test_data_collectors.py
│   ├── test_feature_engineering.py
│   ├── test_integration.py
│   └── test_deployment.py
│
├── trading_bot/                 # 자동매매 봇 모듈
│   ├── config/                # 설정 관리
│   ├── core/                  # 봇 엔진 코어
│   ├── collectors/            # 데이터 수집
│   ├── strategies/            # 매매 전략
│   ├── execution/             # 주문 실행
│   ├── utils/                 # 유틸리티
│   ├── ui/                    # Streamlit UI
│   └── tests/                 # 테스트
│
├── .gitignore                  # Git 제외 파일
├── requirements.txt            # Python 패키지 의존성
├── requirements_trading_bot.txt # Trading Bot 의존성
├── project.db.tar.gz          # DB 압축 파일 (배포용)
├── README.md                   # 프로젝트 메인 README
└── PROJECT_STRUCTURE.md        # 이 파일
```

## 📝 주요 디렉토리 설명

### app/
Streamlit 웹 애플리케이션의 메인 코드
- `main.py`: 앱 진입점 및 라우팅
- `pages/`: 각 기능별 페이지 모듈
- `utils/`: 공통 유틸리티 모듈

### scripts/
데이터 수집, 분석, 유지보수 스크립트
- `collectors/`: 데이터 수집 스크립트
- `analysis/`: 데이터 분석 스크립트
- `maintenance/`: 유지보수 스크립트
- `subprojects/`: 서브 프로젝트 전용 스크립트

### docs/
프로젝트 문서
- `deployment/`: 배포 가이드
- `guides/`: 사용 가이드
- `reports/`: 프로젝트 보고서
- `analysis/`: 데이터 분석 문서

### trading_bot/
자동매매 봇 모듈 (독립적)
- 기존 프로젝트와 완전히 분리된 모듈
- 기존 데이터는 읽기 전용으로 접근

## 🔍 주요 스크립트 위치

### 데이터 수집
- `scripts/collectors/` - 모든 수집 스크립트
- `scripts/subprojects/arbitrage/` - 차익거래 데이터 수집
- `scripts/subprojects/risk_ai/` - 리스크 AI 데이터 수집

### 데이터 분석
- `scripts/analysis/` - 분석 스크립트
- `scripts/subprojects/risk_ai/` - 리스크 분석 스크립트

### 유지보수
- `scripts/maintenance/` - 업데이트/수정 스크립트
- `scripts/sync_sqlite_to_supabase.py` - Supabase 동기화

## 📦 배포 파일

- `requirements.txt`: 메인 프로젝트 의존성
- `requirements_trading_bot.txt`: Trading Bot 의존성
- `project.db.tar.gz`: SQLite DB 압축 파일 (배포용)
- `Dockerfile`, `docker-compose.yml`: Docker 배포 설정

## 🚀 빠른 시작

### 로컬 개발
```bash
# 의존성 설치
pip install -r requirements.txt

# Streamlit 앱 실행
streamlit run app/main.py
```

### 데이터 수집
```bash
# 차익거래 데이터 수집
python scripts/subprojects/arbitrage/fetch_spot_quotes.py

# 리스크 AI 데이터 수집
python scripts/subprojects/risk_ai/fetch_futures_metrics.py
```

### 배포
- Streamlit Cloud: `docs/deployment/README_STREAMLIT_CLOUD.md` 참조
- Docker: `docs/deployment/README_DOCKER.md` 참조
