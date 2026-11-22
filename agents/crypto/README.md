# 코인

코인 투자 후보를 비교하는 분석 경로와 거래소 가격 차이·주문을 다루는 서비스가 있다.

| 업무 | 구현 |
| --- | --- |
| 코인 후보 평가 | 투자 CLI의 `--universe crypto`가 사용하는 [코인 스크리너](screeners/crypto_screener.py) |
| 거래소 가격 차이·백테스트 | [차익거래 모듈](../../scripts/subprojects/arbitrage/) |
| 파생상품·고래 지표 분석 | [Risk AI 모듈](../../scripts/subprojects/risk_ai/) |
| 업비트 자동매매 | [거래 봇과 실행 안내](../../trading_bot/README.md) |

온체인 거래를 수집하고 지갑을 식별하는 코드는 [고래 추적](../whale/)에서 찾을 수 있다.

## 이 폴더의 파일

[collectors/](collectors/) (3개) · [diagnostics/](diagnostics/) (4개) · [docs/](docs/) (35개) · [maintenance/](maintenance/) (6개) · [memos/](memos/) (2개) · [packaging/](packaging/) (3개) · [screeners/](screeners/) (1개) · [sql/](sql/) (2개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=crypto`로 찾을 수 있다.
