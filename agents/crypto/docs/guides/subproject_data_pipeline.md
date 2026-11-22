# 📊 서브 프로젝트 데이터 파이프라인 가이드

이 문서는 발표용 서브 프로젝트(Arbitrage, Risk AI)를 위한 데이터 파이프라인을 정리합니다.

## 1. 목표 요약

| 프로젝트 | 설명 |
|-----------|------|
| **Project 2 (Arbitrage)** | 업비트/KRW와 바이낸스/USDT 간의 시세 괴리(김치 프리미엄)과 펀딩비 트렌드를 분석하여 차익거래 기회를 백테스트 |
| **Project 3 (Risk AI)** | BitInfoCharts 고래 지표와 바이낸스 선물 펀딩/OI 데이터를 결합하여 급격한 변동성/청산 리스크 예측 |

## 2. 데이터 저장소

- **로컬 SQLite**: `data/project.db` (서브 프로젝트 전용 테이블 `upbit_daily`, `binance_spot_daily`, `binance_futures_metrics`, `bitinfocharts_whale`, `exchange_rate`)
- **CSV/임시**: 필요시 `data/` 아래에 추가 저장 가능

## 3. 데이터 수집 스크립트

### 3.1 scripts/subprojects/arbitrage/fetch_spot_quotes.py
- Upbit 일봉: `GET https://api.upbit.com/v1/candles/days`
- Binance 현물일봉: `GET https://api.binance.com/api/v3/klines`
- 환경 변수
  - `UPBIT_MARKETS` (예: `KRW-BTC,KRW-ETH`)
  - `BINANCE_SYMBOLS` (예: `BTCUSDT,ETHUSDT`)
- 데이터 저장: `upbit_daily`, `binance_spot_daily`

### 3.2 scripts/subprojects/risk_ai/fetch_futures_metrics.py
- Binance Futures 펀딩비, OI, 롱/숏, 변동성
- API: `/fapi/v1/fundingRate`, `/fapi/v1/openInterestHist`, `/fapi/v1/ticker/24hr`
- 저장: `binance_futures_metrics`

### 3.3 scripts/subprojects/risk_ai/fetch_bitinfo_whale.py
- BitInfoCharts 고래 클래스 스크래핑 (현재는 BTC/ETH)
- 목표 지표: Top 100 지갑 보유 비중, 평균 트랜잭션 크기
- 저장: `bitinfocharts_whale`

## 4. 초기 설정

1. `pip install -r requirements.txt` (requests, beautifulsoup4, lxml)
2. `.env`에 Upbit/Binance API 키 + 기존 Supabase 키
3. `python3 scripts/maintenance/init_subproject_db.py` 실행하여 SQLite 테이블 생성

## 5. 실행 순서 (예시)

1. `python3 scripts/subprojects/arbitrage/fetch_spot_quotes.py`
2. `python3 scripts/subprojects/risk_ai/fetch_futures_metrics.py`
3. `python3 scripts/subprojects/risk_ai/fetch_bitinfo_whale.py`

## 6. 확장 아이디어

- Exchange rate(`exchange_rate`) 스크립트 추가하여 KRW/USD 환율 확보
- `binance_futures_metrics`에 롱/숏 추세 분석 및 Target Volatility 예측 파이프라인 추가
- `Trade`/`Signal` 테이블을 추가하여 백테스트 결과 저장

## 7. 참고

- sqlite3 CLI: `sqlite3 data/project.db ".tables"`
- DBeaver로 열람 가능: `data/project.db`

