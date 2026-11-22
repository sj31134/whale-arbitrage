# 부동산·법원경매

| 업무 | 호출 경로 | 구현 |
| --- | --- | --- |
| 부동산 후보 평가·배분 | 투자 CLI의 `--universe real_estate` → `run_real_estate_pipeline()` | [부동산 스크리너](screeners/real_estate_screener.py) |
| 토지지분·경매 권리 분석 | `InvestorAgentRunner.run_real_estate_subagent_pipeline()` → `RealEstateSubagent` | [전담 서브에이전트](subagent/) |

두 경로의 호출 관계는 [투자 실행기](../../branch/investor_agent/src/agent/investor_agent_runner.py)에서 확인할 수 있다. 저장된 자료는 [부동산 시장 자료](data/real_estate/)와 [법원경매 자료](data/court_auction/)에 있다.

## 이 폴더의 파일

[data/](data/) (5개) · [graph/](graph/) (1개) · [memos/](memos/) (28개) · [screeners/](screeners/) (1개) · [subagent/](subagent/) (6개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=real_estate`로 찾을 수 있다.
