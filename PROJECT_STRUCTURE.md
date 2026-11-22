# 프로젝트 구조 가이드 (`PROJECT_STRUCTURE.md`)

> **최종 업데이트**: 2026-11-22  
> Streamlit Cloud·Docker·기존 CLI 호환성을 유지하면서 모든 폴더와 파일을 주요 목적별로 재구성했습니다.

---

## 📁 전체 디렉토리 구조

```text
whale_tracking/
├── app/                                # [서비스] Streamlit 암호화폐 차익거래·Risk AI·봇 통합 웹 앱
│   ├── main.py                         # 메인 진입점 (10개 페이지 라우팅 + Cloud 진단)
│   ├── pages/                          # 기능별 페이지 모듈 (10개)
│   └── utils/                          # 데이터 로더, RiskPredictor/Analyzer, SHAP, 추천/계산/시각화 (9개)
│
├── trading_bot/                        # [서비스] 업비트(Upbit) 연동 독립형 자동매매 봇
│   ├── config/                         # 설정 관리 (default_config.json, settings_manager.py)
│   ├── core/                           # 봇 엔진 및 포지션 관리
│   ├── collectors/                     # 실시간 시세·지표 수집
│   ├── strategies/                     # Risk AI 데이터 기반 전략 + 김프 필터
│   ├── execution/                      # 주문 실행 및 잔고 관리
│   ├── ui/                             # Streamlit UI 탭
│   ├── utils/                          # 로거, 텔레그램 알림, 입력 검증
│   └── tests/                          # 봇 단위/통합 테스트
│
├── src/                                # [코어 라이브러리] 재사용 수집 모듈
│   └── collectors/
│       └── multi_chain_collector.py    # 멀티체인(Etherscan v2 등) 고래 트랜잭션 수집기
│
├── scripts/                            # [파이프라인/운영] 목적별 실행 스크립트
│   ├── main/                           # 통합 실행기·일일 업데이트 쉘·체크포인트
│   ├── collectors/                     # 거래소·블록체인·리치리스트 데이터 수집
│   ├── subprojects/                    # 서브프로젝트 코어 엔진
│   │   ├── arbitrage/                  # Project 2: 현물·환율 수집 및 3~4거래소 백테스트
│   │   └── risk_ai/                    # Project 3: 선물/OI/고래 피처, XGBoost/LSTM/SHAP 학습
│   ├── labeling/                       # 거래소 지갑 등록, 라벨링, 거래방향·USD 후처리
│   ├── maintenance/                    # DB 초기화, 스냅샷 빌드, Supabase 동기화, 스키마 엑셀
│   ├── analysis/                       # 수집 커버리지·DB 구조·Top Picks 분석
│   ├── diagnostics/                    # 스키마·타임존·결측·API 디버깅 및 검증 스크립트
│   ├── deploy/                         # Docker·서버·GitHub·ngrok 배포 쉘 스크립트
│   ├── utils/                          # 테이블/업로드/중복 점검 유틸리티
│   ├── tests/                          # 외부 API·스크래핑 수동 테스트 스크립트
│   └── data/                           # 정적 거래소 주소 사전 (known_exchanges.py)
│
├── sql/                                # [데이터베이스] Supabase / PostgreSQL SQL
│   ├── schema/                         # 테이블 생성 DDL 및 컬럼/PK 변경 스키마
│   ├── rpc/                            # Supabase RPC 함수 정의
│   └── batch/                          # 대용량 라벨·거래방향·중복 제거 배치 SQL
│
├── data/                               # [데이터/모델] 시계열 CSV, SQLite 스냅샷, 학습 모델
│   ├── project.db.tar.gz               # 배포용 SQLite 스냅샷 (단일 정본)
│   ├── whale_transactions.csv          # 고래 트랜잭션 아카이브 CSV (95.84 MB)
│   ├── *.csv                           # 거래소 일/주봉, 선물, 환율, 백테스트 결과
│   ├── models/                         # 학습된 XGBoost/Hybrid 모델, 스케일러, 평가 결과
│   ├── analysis/                       # BTC/ETH 고래-가격 상관 및 동적 백테스트 결과
│   └── project3_shap/                  # SHAP 분석 결과 CSV
│
├── tests/                              # [테스트] 코어 수집·피처·통합·배포 자동화 테스트
│
├── docs/                               # [문서] 현역 문서 vs 과거 이력 아카이브 분리
│   ├── README.md                       # 문서 마스터 인덱스
│   ├── architecture/                   # ERD, DB 스키마, 타임존 표준, Project 3 구조
│   ├── guides/                         # API 키, SQL, Trading Bot, 라벨링, 파이프라인 가이드
│   ├── deployment/                     # Streamlit Cloud, Docker, ngrok, 연동·테스트 가이드
│   └── archive/                        # 완료된 시점별 진단·배포·PM 보고서 아카이브
│       ├── analysis/
│       ├── deployment/
│       └── reports/
│
├── branch/                             # [독립 리서치/에이전트 워크스트림]
│   ├── investor_agent/                 # 기관급 멀티에셋 투자 에이전트 (US/KR/JP/CN/Macro/Crypto/RE)
│   │   ├── main.py                     # CLI 오케스트레이터 (9개 유니버스)
│   │   ├── config/                     # 자산군·리스크·스코어링 가중치 YAML
│   │   ├── src/                        # core, data_pipeline, research, strategy, execution, graph, memory, subagents/
│   │   ├── scripts/                    # 시스템 정합성 감사, 지식그래프 동기화, 바이낸스 토큰 스크립트
│   │   ├── data/                       # timeline, memos, memory, graph, order_flow, real_estate, court_auction
│   │   ├── skills/                     # 에이전트 스킬 사본 (.agents/skills와 동기화)
│   │   └── tests/                      # 6개 모듈 단위/통합 테스트 (tmp_path 격리)
│   └── RWATransparency/                # RWA 투명성 디지털 트윈(TDT) 석사 연구 프로젝트
│       ├── dashboard/                  # Streamlit TDT 대시보드
│       ├── scripts/                    # layer1~3 수집/TDT 산출 + analysis(패널 회귀·ML·SHAP)
│       ├── data/                       # raw/ 및 processed/ 패널 데이터
│       └── *.md                        # 논문 본문·초록·비평·결과표
│
├── .agents/skills/                     # [AI 스킬] Antigravity 자동 인식 스킬 정본
│   ├── investor-principles/SKILL.md    # 마스터 투자 원칙·5대 스킬·알고리즘 역공·스트레스 모형
│   └── real-estate-subagent/SKILL.md   # Tier 2-B 부동산·법원경매 전담 스킬
│
├── .streamlit/                         # Streamlit 서버 및 다크 테마 설정
├── .devcontainer/                      # DevContainer 설정
├── Dockerfile                          # Docker 배포 이미지 정의 (app + trading_bot 포함)
├── docker-compose.yml                  # 로컬 Docker Compose
├── docker-compose.prod.yml             # 운영 Docker Compose
├── requirements.txt                    # 메인 의존성
├── requirements_trading_bot.txt        # 자동매매 봇 전용 의존성
├── runtime.txt                         # Python 3.11 런타임 핀
├── build_executable.py                 # 실행파일 패키징 스크립트
├── install_trading_bot.py              # 자동매매 봇 설치 스크립트
└── 코인_데이터스키마_구조.xlsx           # 테이블 스키마 정의 엑셀
```

---

## 🔄 2026-11-22 재구성 주요 변경 요약

1. **`scripts/` 루트 정리**: 흩어져 있던 75개 파일을 `deploy/`, `labeling/`, `diagnostics/`, `collectors/`, `maintenance/`, `main/`, `analysis/`, `tests/`로 100% 분류하고 상대 루트 경로(`PROJECT_ROOT`) 및 내부 참조 경로 일괄 보정.
2. **`sql/` 목적별 분리**: 평면 20개 SQL 파일을 `schema/`(8), `rpc/`(4), `batch/`(8)로 구조화하고 스크립트 내 SQL 경로 보정.
3. **`docs/` 현역·아카이브 분리**: 115개 문서를 현역(`architecture/`, `guides/`, `deployment/`) 33개와 이력(`archive/{analysis,deployment,reports}/`) 81개로 정리.
4. **중복·오염 제거**: 고아 Gitlink(`btc_ledger_research`) 제거, 빈 `scripts/data/project.db*` 및 구버전 루트 `project.db.tar.gz` 정리(`data/project.db.tar.gz` 단일화), `branch/investor_agent/data/memory/` 중복 로그 29개 정리, `.agents/skills`↔`branch/investor_agent/skills` 동기화.
5. **테스트 격리 및 수정**: `branch/investor_agent/tests/` 전체에 `TemporaryDirectory` 격리를 적용해 테스트 실행 시 프로덕션 데이터 오염을 원천 차단하고, `trading_bot`·`tests/test_deployment.py`·`Dockerfile` 결함 수정.
