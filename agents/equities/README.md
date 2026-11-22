# 주식

일반 주식 분석은 하나의 투자 실행기가 시장별 스크리너를 선택해 후보를 평가한다.

| 시장 | 투자 CLI 옵션 | 구현 |
| --- | --- | --- |
| 미국 | `--universe us_equities` | [미국 주식 스크리너](screeners/us_equity_screener.py) |
| 한국 | `--universe kr_equities` | [한국 주식 스크리너](screeners/kr_equity_screener.py) |
| 일본 | `--universe jp_equities` | [일본 주식 스크리너](screeners/jp_equity_screener.py) |
| 중국 | `--universe cn_equities` | [중국 주식 스크리너](screeners/cn_equity_screener.py) |

옵션은 [투자 CLI](../../branch/investor_agent/main.py)에서 선택한다. 미국 주식 후보의 단기 수급과 가격 변곡점은 [미국 소형·고베타 주식 분야](../us_small_cap_high_beta/)에서 다룬다.

## 이 폴더의 파일

[memos/](memos/) (45개) · [screeners/](screeners/) (4개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=equities`로 찾을 수 있다.
