# 고래 추적

보유 코인과 관찰 후보에서 평소와 다른 대형 이동을 찾는다. 체인 거래·주소 라벨·내부 이체 가능성을 대조해 코인 담당에게 해석과 반증 조건을 전달한다. [공통 투자 지침과 정보 범주](../INVESTMENT_MANDATE.md)

[10개 정보 애널리스트](../../data/analysts/README.md)의 종목 근거와 공통 변수를 함께 받으려면 아래 조회 명령에 `--signals`를 추가한다. 로컬 보유분 조회는 `python3 -m private_accounts portfolio-review whale`를 사용한다.

어떤 지갑이 어느 체인에서 얼마를 보냈는지 추적한다. 이 분야는 멀티체인 수집기와 지갑 라벨링 스크립트로 구현되어 있다.

- [체인별 거래 조회](chain/multi_chain_collector.py)
- [등록된 고래 지갑의 거래 수집](collectors/collect_all_whale_transactions.py)
- [지갑 라벨·거래 방향 분류](labeling/)
- [거래 원장](../../data/whale_transactions.csv) · [일별 집계](../../data/whale_daily_stats.csv)

## 이 폴더의 파일

[analysis/](analysis/) (3개) · [chain/](chain/) (1개) · [collectors/](collectors/) (16개) · [data/](data/) (1개) · [diagnostics/](diagnostics/) (9개) · [docs/](docs/) (18개) · [labeling/](labeling/) (27개) · [main/](main/) (3개) · [maintenance/](maintenance/) (18개) · [sql/](sql/) (17개) · [utils/](utils/) (14개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=whale`로 찾을 수 있다.
