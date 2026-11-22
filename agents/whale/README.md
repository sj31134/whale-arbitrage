# 고래 추적

어떤 지갑이 어느 체인에서 얼마를 보냈는지 추적한다. 이 분야는 멀티체인 수집기와 지갑 라벨링 스크립트로 구현되어 있다.

- [체인별 거래 조회](chain/multi_chain_collector.py)
- [등록된 고래 지갑의 거래 수집](collectors/collect_all_whale_transactions.py)
- [지갑 라벨·거래 방향 분류](labeling/)
- [거래 원장](../../data/whale_transactions.csv) · [일별 집계](../../data/whale_daily_stats.csv)

## 이 폴더의 파일

[analysis/](analysis/) (3개) · [chain/](chain/) (1개) · [collectors/](collectors/) (16개) · [data/](data/) (1개) · [diagnostics/](diagnostics/) (9개) · [docs/](docs/) (18개) · [labeling/](labeling/) (27개) · [main/](main/) (3개) · [maintenance/](maintenance/) (18개) · [sql/](sql/) (17개) · [utils/](utils/) (14개)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=whale`로 찾을 수 있다.
