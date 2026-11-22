# 📚 문서 디렉토리 가이드 (`docs/`)

현역으로 참조하는 기술·운영 문서와 과거 시점의 완료/진단 보고서(`archive/`)를 명확히 분리했습니다.

## 📁 디렉토리 구조

```text
docs/
├── README.md                  # 이 파일 (문서 인덱스)
├── architecture/              # DB 스키마, ERD, 타임존 표준, Project 3 설계 (9개)
├── guides/                    # API 키, SQL, Trading Bot, 라벨링, 수집 파이프라인 가이드 (13개)
├── deployment/                # Streamlit Cloud, Docker, ngrok, 연동·테스트 가이드 (11개)
└── archive/                   # 완료된 시점별 보고서·장애진단·PM 로그 (81개)
    ├── analysis/              # 과거 데이터 수집/Project 2·3 진단 보고서 (43개)
    ├── deployment/            # 과거 배포 완료·재배포·점검 로그 (27개)
    └── reports/               # 2025-11-30 PM 업무지시서·진행/완료·메뉴 리뷰 (11개)
```

---

## 🔖 핵심 현역 문서 바로가기

### 1. 아키텍처 & 스키마 (`docs/architecture/`)
- [ERD.md](./architecture/ERD.md) — 데이터베이스 ERD
- [DB_구조_분석_요약.md](./architecture/DB_구조_분석_요약.md) — 테이블 구조 요약
- [메뉴별_테이블_및_데이터_기간_정리.md](./architecture/메뉴별_테이블_및_데이터_기간_정리.md) — 앱 페이지별 DB 매핑
- [timezone_standard.md](./architecture/timezone_standard.md) — UTC/KST 타임존 표준
- [project3_summary.md](./architecture/project3_summary.md) — Project 3(Risk AI) 요약

### 2. 운영 & 개발 가이드 (`docs/guides/`)
- [API_키_발급_가이드.md](./guides/API_키_발급_가이드.md) — 거래소·블록체인 API 키 설정
- [SQL_실행_가이드.md](./guides/SQL_실행_가이드.md) — Supabase SQL 실행 절차
- [subproject_data_pipeline.md](./guides/subproject_data_pipeline.md) — Arbitrage & Risk AI 파이프라인
- [TRADING_BOT_ARCHITECTURE.md](./guides/TRADING_BOT_ARCHITECTURE.md) / [TRADING_BOT_GUIDE.md](./guides/TRADING_BOT_GUIDE.md) — 업비트 자동매매 봇
- [FAST_LABEL_UPDATE_GUIDE.md](./guides/FAST_LABEL_UPDATE_GUIDE.md) / [TRANSACTION_DIRECTION_GUIDE.md](./guides/TRANSACTION_DIRECTION_GUIDE.md) — 고래 라벨·거래방향 업데이트

### 3. 배포 가이드 (`docs/deployment/`)
- [README_STREAMLIT_CLOUD.md](./deployment/README_STREAMLIT_CLOUD.md) / [STREAMLIT_CLOUD_TROUBLESHOOTING.md](./deployment/STREAMLIT_CLOUD_TROUBLESHOOTING.md)
- [README_DOCKER.md](./deployment/README_DOCKER.md) / [docker_deployment_guide.md](./deployment/docker_deployment_guide.md) / [docker_troubleshooting.md](./deployment/docker_troubleshooting.md)
- [README_NGROK.md](./deployment/README_NGROK.md) / [README_DEPLOY.md](./deployment/README_DEPLOY.md)
- [DEPLOYMENT_CHECKLIST.md](./deployment/DEPLOYMENT_CHECKLIST.md) / [전체_페이지_테스트_가이드.md](./deployment/전체_페이지_테스트_가이드.md)
