# 미국 소형·고베타 주식

미국 주식 중 시총·베타가 확인된 종목의 촉매와 급락·희석·매도 유동성 위험을 평가한다. 보유분은 주식 담당과 한 번만 집계하고 연구 후보의 코어 편입은 사용자 검토를 거친다. [공통 투자 지침과 정보 범주](../INVESTMENT_MANDATE.md)

[10개 정보 애널리스트](../../data/analysts/README.md)의 종목 근거와 공통 변수를 함께 받으려면 아래 조회 명령에 `--signals`를 추가한다. 로컬 보유분 조회는 `python3 -m private_accounts portfolio-review us_small_cap_high_beta`를 사용한다.

이 분야와 연결된 기존 구현은 텐배거 후보의 수급과 가격 변곡점을 분석하는 `OrderFlowSubagent`다.

[투자 CLI](../../branch/investor_agent/main.py)에서 `--universe order_flow --market us`를 선택하면 등록된 후보 중 미국 시장 종목을 가져온다. [후보 선택 코드](order_flow/universe_collector.py)는 여기서 시가총액 상한이나 시장 대비 베타 하한을 적용하지 않는다. 따라서 결과에는 TSLA, MU처럼 등록 목록에 함께 있는 종목도 포함된다.

- [수급 분석 서브에이전트](order_flow/order_flow_subagent.py)
- [10달러 전후 가격 변곡점 분석](order_flow/ten_dollar_inflection_engine.py)
- [수급 데이터](data/order_flow/) · [기존 분석 메모](memos/ORDER_FLOW_TRADING_MEMO.md)

## 이 폴더의 파일

[data/](data/) (2개) · [memos/](memos/) (2개) · [order_flow/](order_flow/) (11개) · [scripts/](scripts/) (2개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=us_small_cap_high_beta`로 찾을 수 있다.
