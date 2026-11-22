# whale_tracking 폴더 구조

분야별 구현과 분석 자료의 실제 위치는 `agents/`다. 공용 실행기, 서비스 배포 경로, 자동 테스트, 독립 RWA 연구는 아래 표의 경로를 사용한다. [전체 폴더트리](agents/FILE_TREE.md)에서 분야별 파일을 펼쳐 볼 수 있다. [전체 파일 분류표](agents/FILE_MAP.csv)에서 파일명으로 검색하거나 `owner`로 필터링할 수 있다.

## 에이전트 폴더트리

| 폴더 | 실제 하위 폴더 | 담당 업무 |
| --- | --- | --- |
| [agents/whale/](agents/whale/) | `chain/`, `collectors/`, `data/`, `labeling/`, `analysis/`, `diagnostics/`, `main/`, `maintenance/`, `utils/`, `sql/`, `docs/` | 멀티체인 거래 수집, 고래 지갑 식별, 라벨링·거래 방향 집계 |
| [agents/crypto/](agents/crypto/) | `screeners/`, `collectors/`, `diagnostics/`, `maintenance/`, `packaging/`, `sql/`, `memos/`, `docs/` | 코인 투자 후보, 거래소 시세, 차익거래·Risk AI 운영 자료, 봇 패키징 |
| [agents/real_estate/](agents/real_estate/) | `screeners/`, `subagent/`, `graph/`, `data/{court_auction,real_estate,graph}/`, `memos/` | 부동산 평가, 경매 수집·권리 분석, 부동산 지식그래프 |
| [agents/equities/](agents/equities/) | `screeners/`, `memos/` | 미국·한국·일본·중국 주식 후보 평가와 종목별 메모 |
| [agents/us_small_cap_high_beta/](agents/us_small_cap_high_beta/) | `order_flow/`, `scripts/`, `data/order_flow/`, `memos/` | 단기 수급·가격 변곡점 분석. 구현은 한국·미국 및 토큰화 자산 경로를 공유한다 |

미국 시장은 투자 CLI의 `--universe order_flow --market us`로 선택한다. 이 옵션의 종목 필터는 거래 시장을 확인하며 시가총액이나 베타 기준은 적용하지 않는다.

## 공용 코드·데이터와 기존 진입점

| 위치 | 담당 범위 |
| --- | --- |
| [branch/investor_agent/](branch/investor_agent/) | 공용 CLI·투자 실행기, 평가·전략·리스크·메모리, 거시경제 분석, 설정·포트폴리오 타임라인 |
| [private_accounts/](private_accounts/README.md) | 로컬 조회 전용 계좌 수집기, 개인 잔고 DB 관리, 개인 화면 |
| [app/](app/) · [trading_bot/](trading_bot/) | Streamlit 앱과 업비트 자동매매 서비스 |
| [scripts/subprojects/](scripts/subprojects/) | 기존 차익거래·Risk AI 패키지와 백테스트 진입점 |
| [data/](data/) | 운영 SQLite 스냅샷, 고래 거래 원장, 거래소 데이터, 학습 모델 |
| [scripts/](scripts/) · [sql/](sql/) · [src/](src/) | 공용 운영 도구와 기존 스크립트·SQL·Python 경로. 이동한 파일의 이전 위치에는 상대 심볼릭 링크가 있다. |
| [docs/](docs/) | 공용 아키텍처·배포·과거 보고서와 분야별 문서 인덱스 |
| [tests/](tests/) · [투자 테스트](branch/investor_agent/tests/) · [봇 테스트](trading_bot/tests/) | 기존 테스트 수집 위치. 파일별 담당 분야는 분류표에 표시한다. |
| [branch/RWATransparency/](branch/RWATransparency/) | 실물자산 토큰의 투명성에 관한 독립 연구, 원자료, 분석 코드, 논문, 대시보드 |
| `.agents/skills/` | 투자 원칙과 부동산·경매 분석 지침 원본 |
| 루트 설정 | Docker·Compose·Streamlit 설정, 패키지 의존성, Python 버전, 프로젝트 안내 |

기존 CLI 및 Python 모듈 경로는 계속 사용할 수 있다. Git 체크아웃에서 심볼릭 링크가 실제 링크로 복원되어야 한다. 커스텀 `--export-memos` 경로는 지정한 폴더에 파일을 쓴다. 기본 출력에서는 종목별 메모가 분야별 `memos/`에 저장되고 `branch/investor_agent/data/memos/`에서도 같은 파일을 열 수 있다.

## 이전 구조 변경 이력 (958d5a5)

1. **`scripts/` 루트 정리**: 흩어져 있던 75개 파일을 `deploy/`, `labeling/`, `diagnostics/`, `collectors/`, `maintenance/`, `main/`, `analysis/`, `tests/`로 100% 분류하고 상대 루트 경로(`PROJECT_ROOT`) 및 내부 참조 경로 일괄 보정.
2. **`sql/` 목적별 분리**: 평면 20개 SQL 파일을 `schema/`(8), `rpc/`(4), `batch/`(8)로 구조화하고 스크립트 내 SQL 경로 보정.
3. **`docs/` 현역·아카이브 분리**: 115개 문서를 현역(`architecture/`, `guides/`, `deployment/`) 33개와 이력(`archive/{analysis,deployment,reports}/`) 81개로 정리.
4. **중복·오염 제거**: 고아 Gitlink(`btc_ledger_research`) 제거, 빈 `scripts/data/project.db*` 및 구버전 루트 `project.db.tar.gz` 정리(`data/project.db.tar.gz` 단일화), `branch/investor_agent/data/memory/` 중복 로그 29개 정리, `.agents/skills`↔`branch/investor_agent/skills` 동기화.
5. **테스트 격리 및 수정**: `branch/investor_agent/tests/` 전체에 `TemporaryDirectory` 격리를 적용해 테스트 실행 시 프로덕션 데이터 오염을 원천 차단하고, `trading_bot`·`tests/test_deployment.py`·`Dockerfile` 결함 수정.
