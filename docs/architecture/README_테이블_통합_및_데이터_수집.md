# 📊 테이블 통합 및 데이터 수집 가이드

## 🎯 목표
1. `market_data_daily` 테이블을 `price_history` 테이블로 통합
2. 바이낸스에서 9개 코인의 거래 기록을 수집하여 `price_history`에 저장
3. `whale_address`에 있는 고래 지갑 주소의 거래 기록만 `whale_transactions`에 추가

---

## 📋 작업 순서

### 1단계: 테이블 통합 (SQL 실행)

#### 1.1 Supabase SQL Editor에서 실행
1. Supabase 대시보드 접속
2. 좌측 메뉴에서 'SQL Editor' 클릭
3. 'New query' 클릭
4. 다음 파일의 SQL을 복사해서 실행:
   ```
   sql/merge_market_data_daily_to_price_history.sql
   ```

#### 1.2 실행 내용
- `price_history` 테이블에 `market_data_daily`의 컬럼 추가:
  - `date` (DATE)
  - `price_change_24h` (NUMERIC)
  - `price_change_percent_24h` (NUMERIC)
  - `weighted_avg_price` (NUMERIC)
  - `prev_close_price` (NUMERIC)
  - `last_price` (NUMERIC)
  - `bid_price` (NUMERIC)
  - `ask_price` (NUMERIC)
  - `first_trade_id` (BIGINT)
  - `last_trade_id` (BIGINT)
  - `open_time` (TIMESTAMPTZ)
  - `close_time` (TIMESTAMPTZ)
- `market_data_daily`의 데이터를 `price_history`로 마이그레이션
- 인덱스 추가

---

### 2단계: 바이낸스 거래 기록 수집

#### 2.1 스크립트 실행
```bash
cd /Users/junyonglee/Documents/GitHub/whale_tracking
conda activate whale_tracking
python collect_binance_trades_for_whale_addresses.py
```

#### 2.2 수집 대상 코인
- BTC → BTCUSDT
- ETH → ETHUSDT
- LTC → LTCUSDT
- DOGE → DOGEUSDT
- VTC → VTCUSDT
- BSC → BNBUSDT
- DOT → DOTUSDT
- LINK → LINKUSDT
- SOL → SOLUSDT

#### 2.3 수집 데이터
- K-line 데이터 (1시간 간격, 최근 500건)
- `price_history` 테이블에 저장

---

### 3단계: 고래 지갑 주소 거래 기록 수집

#### 3.1 환경 변수 설정
`.env` 파일에 다음 추가:
```env
ETHERSCAN_API_KEY=your_etherscan_api_key
BSCSCAN_API_KEY=your_bscscan_api_key
```

#### 3.2 API 키 발급
- **Etherscan**: https://etherscan.io/apis
- **BSCScan**: https://bscscan.com/apis

#### 3.3 스크립트 실행
```bash
python collect_whale_transactions_from_blockchain.py
```

#### 3.4 수집 방식
- **Ethereum (ETH)**: Etherscan API 사용
- **BSC**: BSCScan API 사용
- **Bitcoin (BTC)**: BlockCypher API 또는 Blockchain.info API 사용 (추가 구현 필요)
- **기타 체인**: 각 체인별 블록체인 탐색기 API 사용

---

## ⚠️ 주의사항

### 바이낸스 API 제한
- 바이낸스 API는 **개별 지갑 주소의 거래 기록을 제공하지 않습니다**
- `price_history`는 시장 전체의 가격 데이터입니다
- 고래 지갑 주소의 실제 거래 기록은 **블록체인 탐색기 API**를 사용해야 합니다

### 블록체인별 API
| 체인 | API | URL |
|------|-----|-----|
| Ethereum | Etherscan | https://etherscan.io/apis |
| BSC | BSCScan | https://bscscan.com/apis |
| Bitcoin | BlockCypher | https://www.blockcypher.com/dev/bitcoin/ |
| Bitcoin | Blockchain.info | https://www.blockchain.com/api |
| Polygon | PolygonScan | https://polygonscan.com/apis |
| Avalanche | SnowTrace | https://snowtrace.io/apis |

---

## 📝 파일 구조

```
whale_tracking/
├── sql/
│   └── merge_market_data_daily_to_price_history.sql  # 테이블 통합 SQL
├── collect_binance_trades_for_whale_addresses.py     # 바이낸스 데이터 수집
├── collect_whale_transactions_from_blockchain.py      # 블록체인 거래 기록 수집
└── README_테이블_통합_및_데이터_수집.md              # 이 파일
```

---

## 🔄 데이터 흐름

```
1. market_data_daily → price_history (통합)
   ↓
2. 바이낸스 API → price_history (가격 데이터)
   ↓
3. 블록체인 탐색기 API → whale_transactions (고래 거래 기록)
   ↓
4. whale_address (고래 지갑 주소) → 필터링 → whale_transactions
```

---

## ✅ 체크리스트

### 테이블 통합
- [ ] `merge_market_data_daily_to_price_history.sql` 실행
- [ ] `price_history` 테이블에 컬럼 추가 확인
- [ ] `market_data_daily` 데이터 마이그레이션 확인

### 바이낸스 데이터 수집
- [ ] `collect_binance_trades_for_whale_addresses.py` 실행
- [ ] 9개 코인의 데이터가 `price_history`에 저장되었는지 확인

### 블록체인 거래 기록 수집
- [ ] API 키 발급 및 `.env` 파일에 추가
- [ ] `collect_whale_transactions_from_blockchain.py` 실행
- [ ] 고래 지갑 주소의 거래 기록이 `whale_transactions`에 저장되었는지 확인

---

## 🐛 문제 해결

### API 키 오류
- API 키가 올바르게 설정되었는지 확인
- API 키의 rate limit 확인

### 데이터 중복
- `upsert`를 사용하여 중복 데이터 방지
- `tx_hash`를 기준으로 중복 체크

### Rate Limit
- API 호출 간 적절한 딜레이 추가
- 배치 처리로 API 호출 최소화

---

## 📚 참고 자료

- [바이낸스 API 문서](https://binance-docs.github.io/apidocs/spot/en/)
- [Etherscan API 문서](https://docs.etherscan.io/)
- [BSCScan API 문서](https://docs.bscscan.com/)



