# 부동산·법원경매

보유 실물의 순현금흐름·부채 만기·보증금 반환 능력을 점검한다. 후보 물건은 실거래·토지지분·공급·권리 인수액을 원문과 대조하고 총필요현금을 산출한다. [공통 투자 지침과 정보 범주](../INVESTMENT_MANDATE.md)

[10개 정보 애널리스트](../../data/analysts/README.md)의 종목 근거와 공통 변수를 함께 받으려면 아래 조회 명령에 `--signals`를 추가한다. 로컬 보유분 조회는 `python3 -m private_accounts portfolio-review real_estate`를 사용한다.

| 업무 | 호출 경로 | 구현 |
| --- | --- | --- |
| 부동산 후보 평가·배분 | 투자 CLI의 `--universe real_estate` → `run_real_estate_pipeline()` | [부동산 스크리너](screeners/real_estate_screener.py) |
| 토지지분·경매 권리 분석 | `InvestorAgentRunner.run_real_estate_subagent_pipeline()` → `RealEstateSubagent` | [전담 서브에이전트](subagent/) |

두 경로의 호출 관계는 [투자 실행기](../../branch/investor_agent/src/agent/investor_agent_runner.py)에서 확인할 수 있다. 저장된 자료는 [부동산 시장 자료](data/real_estate/)와 [법원경매 자료](data/court_auction/)에 있다.

## 이 폴더의 파일

[data/](data/) (5개) · [graph/](graph/) (1개) · [memos/](memos/) (28개) · [screeners/](screeners/) (1개) · [subagent/](subagent/) (6개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=real_estate`로 찾을 수 있다.
