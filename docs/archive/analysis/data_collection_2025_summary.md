# 2025년 데이터 수집 작업 요약

## 완료된 작업

### 1. 타임존 확인 스크립트 생성
- ✅ `scripts/check_timezone_price_history.py`: price_history 테이블 타임존 확인
- ✅ `scripts/check_timezone_whale_transactions.py`: whale_transactions 테이블 타임존 확인
- ✅ `docs/timezone_analysis.md`: 타임존 분석 결과 문서

### 2. market_cap_data vs price_history 분석
- ✅ `docs/market_cap_vs_price_history_analysis.md`: 테이블 비교 분석 문서
- **결론**: 두 테이블은 목적이 다르므로 별도 유지 권장

### 3. 1시간 단위 가격 데이터 수집 스크립트
- ✅ `collect_price_history_hourly.py`: 모든 주요 코인에 대해 1시간 간격 가격 데이터 수집
- **대상 코인**: BTC, ETH, BNB, USDC, XRP, LTC, DOGE, LINK, SOL, DOT
- **기간**: 2025년 1월 1일 ~ 오늘
- **API**: Binance API (interval='1h')
- **타임존**: UTC 명시적으로 처리

### 4. BTC 고래 거래 데이터 보충 스크립트
- ✅ `collect_btc_whale_transactions.py`: BTC 고래 거래 데이터 수집
- **API**: Blockstream API (무료, 제한 없음)
- **기간**: 2025년 1월 1일 ~ 오늘
- **타임존**: UTC 명시적으로 처리

### 5. 데이터 검증 스크립트
- ✅ `scripts/verify_data_collection_2025.py`: 수집된 데이터의 완전성 검증
- **검증 항목**:
  - price_history: 코인별, 날짜별 데이터 수 확인
  - whale_transactions: 코인별, 날짜별 거래 수 확인

### 6. 통합 실행 스크립트
- ✅ `run_data_collection_2025.py`: 모든 데이터 수집 작업을 순차적으로 실행

## 실행 방법

### 1. 타임존 확인
```bash
# price_history 타임존 확인
python scripts/check_timezone_price_history.py

# whale_transactions 타임존 확인
python scripts/check_timezone_whale_transactions.py
```

### 2. 데이터 수집
```bash
# 통합 실행 (권장)
python run_data_collection_2025.py

# 또는 개별 실행
python collect_price_history_hourly.py
python collect_btc_whale_transactions.py
```

### 3. 데이터 검증
```bash
python scripts/verify_data_collection_2025.py
```

## 주요 개선 사항

### 타임존 처리
- 모든 타임스탬프를 UTC로 명시적으로 저장
- `datetime.fromtimestamp(..., tz=timezone.utc)` 사용
- ISO 형식 저장 시 타임존 정보 포함

### 데이터 수집
- 1시간 단위 세밀한 데이터 수집
- 페이지네이션 지원으로 대량 데이터 수집 가능
- 중복 데이터 자동 처리 (upsert 사용)

### BTC 데이터 보충
- Blockstream API 활용 (무료, 제한 없음)
- whale_address 테이블의 모든 BTC 주소 처리
- 날짜 범위 필터링으로 효율적 수집

## 다음 단계

1. **타임존 확인 스크립트 실행**: 실제 데이터베이스의 타임존 확인
2. **데이터 수집 실행**: `run_data_collection_2025.py` 실행
3. **데이터 검증**: 수집 완료 후 검증 스크립트 실행
4. **기존 코드 개선**: 타임존 처리 개선이 필요한 기존 스크립트 수정

## 주의사항

- 데이터 수집은 시간이 오래 걸릴 수 있습니다 (API rate limit 고려)
- Binance API는 분당 요청 제한이 있으므로 적절한 딜레이 포함
- Blockstream API는 무료이지만 과도한 요청 시 제한될 수 있음

## 파일 구조

```
whale_tracking/
├── collect_price_history_hourly.py          # 1시간 단위 가격 데이터 수집
├── collect_btc_whale_transactions.py        # BTC 고래 거래 데이터 수집
├── run_data_collection_2025.py              # 통합 실행 스크립트
├── scripts/
│   ├── check_timezone_price_history.py      # price_history 타임존 확인
│   ├── check_timezone_whale_transactions.py # whale_transactions 타임존 확인
│   └── verify_data_collection_2025.py       # 데이터 검증
└── docs/
    ├── timezone_analysis.md                 # 타임존 분석 문서
    ├── market_cap_vs_price_history_analysis.md  # 테이블 비교 분석
    └── data_collection_2025_summary.md      # 이 문서
```

