# 코인

보유 코인의 가치 귀속·거래소 집중과 회수 가능성을 점검한다. 후보는 공급 해제·사용량·현물 유동성을 확인하고, 고래 흐름과 파생 수급을 보조 근거로 사용한다. [공통 투자 지침과 정보 범주](../INVESTMENT_MANDATE.md)

[10개 정보 애널리스트](../../data/analysts/README.md)의 종목 근거와 공통 변수를 함께 받으려면 아래 조회 명령에 `--signals`를 추가한다. 로컬 보유분 조회는 `python3 -m private_accounts portfolio-review crypto`를 사용한다.

코인 투자 후보와 거래소 가격 차이를 분석한다. 업비트 봇의 직접 주문은 보류 중이다.

| 업무 | 구현 |
| --- | --- |
| 코인 후보 평가 | 투자 CLI의 `--universe crypto`가 사용하는 [코인 스크리너](screeners/crypto_screener.py) |
| 거래소 가격 차이·백테스트 | [차익거래 모듈](../../scripts/subprojects/arbitrage/) |
| 파생상품·고래 지표 분석 | [Risk AI 모듈](../../scripts/subprojects/risk_ai/) |
| 업비트 자동매매 | [거래 봇 보류 상태](../../trading_bot/README.md) |

온체인 거래를 수집하고 지갑을 식별하는 코드는 [고래 추적](../whale/)에서 찾을 수 있다.

## 이 폴더의 파일

[collectors/](collectors/) (3개) · [diagnostics/](diagnostics/) (4개) · [docs/](docs/) (35개) · [maintenance/](maintenance/) (6개) · [memos/](memos/) (2개) · [packaging/](packaging/) (3개) · [screeners/](screeners/) (1개) · [sql/](sql/) (2개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=crypto`로 찾을 수 있다.
