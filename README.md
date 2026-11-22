# 🐋 Whale Tracking & Multi-Asset Research Monorepo

암호화폐 고래 추적·차익거래·Risk AI 웹 플랫폼, 업비트 자동매매 봇, 기관급 멀티에셋 투자 에이전트(`branch/investor_agent`), RWA 투명성 연구(`branch/RWATransparency`)를 목적별 폴더로 체계화한 통합 저장소입니다.

> 상세 폴더·파일 구조는 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) 및 [docs/README.md](./docs/README.md)를 참조하세요.

[프로젝트 목표·운영 지침·검증 명령](AGENTS.md)에서 분석과 계좌 관리의 기준을 확인할 수 있습니다.

[전체 폴더트리](agents/FILE_TREE.md)와 [파일 분류표](agents/FILE_MAP.csv)에서 담당 분야와 실제 위치를 확인할 수 있습니다. 분야별 코드와 데이터는 [고래](agents/whale/), [코인](agents/crypto/), [부동산](agents/real_estate/), [주식](agents/equities/), [미국 소형·고베타 주식](agents/us_small_cap_high_beta/)에서 찾을 수 있습니다.

---

## 🧭 주요 워크스트림 구성

| 영역 | 경로 | 설명 |
| :--- | :--- | :--- |
| **1. Crypto Web App (Arbitrage & Risk AI)** | `app/`, `src/`, `scripts/`, `sql/`, `data/` | Streamlit 10페이지 분석 대시보드, 멀티체인 고래 수집, 파생/고래 기반 Risk AI 모델 |
| **2. Upbit Auto Trading Bot** | `trading_bot/` | `data/project.db` 읽기 전용 연동, Risk AI + 김치 프리미엄 필터 기반 자동매매 봇 |
| **3. Institutional Investor Agent** | `branch/investor_agent/` | 글로벌 멀티에셋(US/KR/JP/CN/Macro/Crypto/RE) + Order Flow·부동산/경매 서브에이전트 + 5-Factor 타이밍 엔진 |
| **4. RWA Transparency Research** | `branch/RWATransparency/` | TDT(Transparency Digital Twin) 3계층 지표, 패널 회귀·SHAP 분석, 논문 및 대시보드 |
| **5. Agent Skills** | `.agents/skills/` | Antigravity AI 에이전트용 투자 원칙 및 부동산/경매 전담 스킬 명세 |

---

개인 Mac에서 관리하는 여섯 기관의 잔고와 등록 절차는 [개인 계좌 관리](private_accounts/README.md)에서 확인할 수 있습니다.

## 🚀 빠른 시작

### 1) 암호화폐 분석 웹 앱 (Streamlit)
```bash
pip install -r requirements.txt
export USE_LOCAL_DB=1          # 로컬 SQLite(data/project.db)만 사용 시
streamlit run app/main.py      # http://localhost:8501
```

### 2) 데이터 수집·업데이트 및 라벨링
```bash
# 오늘 기준 통합 데이터 업데이트 (현물·환율·선물·고래 통계)
./scripts/main/run_data_update_to_today.sh

# 병렬 고래 데이터 수집
python3 scripts/main/run_parallel_collection.py

# 라벨·트랜잭션 방향 업데이트
python3 scripts/labeling/update_labels_stable.py
python3 scripts/labeling/update_direction_direct.py

# 차익거래 / Risk AI 개별 수집
python3 scripts/subprojects/arbitrage/fetch_spot_quotes.py
python3 scripts/subprojects/risk_ai/fetch_futures_metrics.py
```

### 3) 기관급 멀티에셋 투자 에이전트 (`branch/investor_agent`)
```bash
python3 branch/investor_agent/main.py --universe multi
python3 branch/investor_agent/main.py --universe order_flow --market all
python3 branch/investor_agent/main.py --universe real_estate
```

### 4) RWA Transparency 대시보드 (`branch/RWATransparency`)
```bash
streamlit run branch/RWATransparency/dashboard/app.py
```

---

## ⚙️ 환경 설정

`config/.env` 파일에 Supabase 및 API 키를 설정합니다 (상세: [docs/guides/API_키_발급_가이드.md](./docs/guides/API_키_발급_가이드.md)):
```env
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_key
```

---

## 🐳 배포 및 테스트

### 배포 가이드 (`docs/deployment/`)
- **Streamlit Cloud**: [docs/deployment/README_STREAMLIT_CLOUD.md](./docs/deployment/README_STREAMLIT_CLOUD.md)
- **Docker 로컬/운영**: [docs/deployment/README_DOCKER.md](./docs/deployment/README_DOCKER.md) / `docker-compose up -d --build`
- **Docker + ngrok**: [docs/deployment/README_NGROK.md](./docs/deployment/README_NGROK.md)
- **서버 배포 스크립트**: `./scripts/deploy/deploy_to_server.sh` ([docs/deployment/README_DEPLOY.md](./docs/deployment/README_DEPLOY.md))

### 테스트 실행
```bash
# 코어 수집·피처·통합·배포 테스트
pytest tests -v

# 멀티에셋 투자 에이전트 전체 테스트 (tmp_path 격리)
pytest branch/investor_agent/tests -v

# 트레이딩 봇 단위 테스트
pytest trading_bot/tests/test_settings_manager.py trading_bot/tests/test_data_collector.py -v
```
