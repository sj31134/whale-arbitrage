# 분야별 파일

| 분야 | 먼저 볼 폴더 |
| --- | --- |
| [고래](whale/) | [체인 수집기](whale/chain/), [지갑 수집](whale/collectors/), [라벨링](whale/labeling/) |
| [코인](crypto/) | [시세 수집](crypto/collectors/), [코인 스크리너](crypto/screeners/), [운영 문서](crypto/docs/) |
| [부동산](real_estate/) | [부동산·경매 분석 코드](real_estate/subagent/), [경매 데이터](real_estate/data/court_auction/), [메모](real_estate/memos/) |
| [주식](equities/) | [국가별 스크리너](equities/screeners/), [종목 메모](equities/memos/) |
| [미국 소형·고베타 주식](us_small_cap_high_beta/) | [수급 엔진](us_small_cap_high_beta/order_flow/), [수급 데이터](us_small_cap_high_beta/data/order_flow/), [분석 메모](us_small_cap_high_beta/memos/) |

[전체 폴더트리](FILE_TREE.md)에서 분야를 펼치면 모든 하위 폴더와 파일을 볼 수 있다.

## 파일 하나 찾기

[FILE_MAP.csv](FILE_MAP.csv)에 버전 관리 대상 원본 파일을 한 행씩 기록한다. `owner`는 주 담당 분야, `path`는 저장소 루트 기준 실제 경로다. 이동한 파일은 `previous_path`에 기존 호환 경로가 있다. `shared`는 공용 운영·투자 기능, `rwa_research`는 독립 RWA 연구다.

`placement`가 `agent`이면 분야 폴더에 원본이 있다. `protected`는 배포·데이터·스킬 호환 경로, `tests`는 기존 테스트 수집 위치, `shared_store`는 여러 자산을 한 인덱스로 관리하는 투자 메모리, `shared`는 공용 경로, `research`는 독립 연구 경로다. 운영 중 생성되는 무시 파일과 Git 내부 파일은 집계에서 제외한다.

파일을 추가하거나 이동하면 분류표를 갱신하고 `python3 scripts/maintenance/check_agent_layout.py --write-tree`로 트리를 다시 만든다. 저장소 루트에서 `python3 scripts/maintenance/check_agent_layout.py`를 실행하면 누락된 파일과 끊어진 호환 경로를 찾을 수 있다.
