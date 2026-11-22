# market_cap_data vs price_history 테이블 비교 분석

## 1. 테이블 구조 비교

### market_cap_data 테이블
**목적**: 시가총액 및 메타데이터 중심

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | 고유 ID (PK) |
| crypto_id | UUID | 암호화폐 ID (FK) |
| timestamp | TIMESTAMPTZ | 타임스탬프 |
| market_cap | NUMERIC | 시가총액 |
| market_cap_rank | INTEGER | 시가총액 순위 |
| fully_diluted_market_cap | NUMERIC | 완전 희석 시가총액 |
| circulating_supply | NUMERIC | 유통 공급량 |
| total_supply | NUMERIC | 총 공급량 |
| max_supply | NUMERIC | 최대 공급량 |
| market_cap_dominance | NUMERIC | 시가총액 점유율 |
| ath_price | NUMERIC | 역대 최고가 |
| ath_date | TIMESTAMPTZ | 역대 최고가 날짜 |
| ath_change_percentage | NUMERIC | 역대 최고가 변동률 |
| atl_price | NUMERIC | 역대 최저가 |
| atl_date | TIMESTAMPTZ | 역대 최저가 날짜 |
| atl_change_percentage | NUMERIC | 역대 최저가 변동률 |
| data_source | VARCHAR | 데이터 출처 |
| raw_data | JSONB | 원시 데이터 |
| created_at | TIMESTAMPTZ | 생성일시 |

### price_history 테이블
**목적**: 가격 및 거래량 데이터 중심

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | 고유 ID (PK) |
| crypto_id | UUID | 암호화폐 ID (FK) |
| timestamp | TIMESTAMPTZ | 타임스탬프 |
| open_price | NUMERIC | 시가 |
| high_price | NUMERIC | 고가 |
| low_price | NUMERIC | 저가 |
| close_price | NUMERIC | 종가 |
| volume | NUMERIC | 거래량 |
| quote_volume | NUMERIC | 기준 통화 거래량 |
| trade_count | INTEGER | 거래 수 |
| taker_buy_volume | NUMERIC | 매수 거래량 |
| taker_buy_quote_volume | NUMERIC | 매수 기준 통화 거래량 |
| date | DATE | 날짜 (추가됨) |
| price_change_24h | NUMERIC | 24시간 가격 변동 |
| price_change_percent_24h | NUMERIC | 24시간 가격 변동률 |
| weighted_avg_price | NUMERIC | 가중 평균 가격 |
| prev_close_price | NUMERIC | 이전 종가 |
| last_price | NUMERIC | 최종 가격 |
| bid_price | NUMERIC | 매수 호가 |
| ask_price | NUMERIC | 매도 호가 |
| first_trade_id | BIGINT | 첫 거래 ID |
| last_trade_id | BIGINT | 마지막 거래 ID |
| open_time | TIMESTAMPTZ | 시작 시간 |
| close_time | TIMESTAMPTZ | 종료 시간 |
| data_source | VARCHAR | 데이터 출처 |
| raw_data | JSONB | 원시 데이터 |
| created_at | TIMESTAMPTZ | 생성일시 |

## 2. 데이터 특성 비교

### market_cap_data
- **데이터 주기**: 일반적으로 일일 또는 주기적 스냅샷
- **데이터 특성**: 
  - 시가총액, 순위 등 메타데이터
  - 공급량 정보 (circulating, total, max)
  - 역대 최고가/최저가 정보
  - 시장 점유율 정보
- **업데이트 빈도**: 낮음 (일일 또는 그 이하)
- **용도**: 
  - 코인 순위 추적
  - 시가총액 변화 분석
  - 공급량 추적

### price_history
- **데이터 주기**: 1시간 단위 (또는 더 세밀한 간격)
- **데이터 특성**:
  - OHLC 가격 데이터
  - 거래량 정보
  - 실시간 가격 변동
- **업데이트 빈도**: 높음 (1시간마다 또는 실시간)
- **용도**:
  - 가격 차트 분석
  - 거래량 분석
  - 고래 거래와 가격 상관관계 분석

## 3. 코드베이스 사용 현황

### market_cap_data
- **사용 여부**: ❌ 코드베이스에서 사용되지 않음
- **참조 파일**: 
  - `generate_schema_excel.py` (스키마 정의만)
  - `ERD.md` (ERD 다이어그램)
  - `analyze_db_structure.py` (테이블 목록만)
- **결론**: 현재 프로젝트에서 실제로 사용되지 않는 테이블

### price_history
- **사용 여부**: ✅ 활발히 사용 중
- **참조 파일**:
  - `collect_price_history_for_usdc_bnb_xrp.py` (데이터 수집)
  - `collect_binance_trades_for_whale_addresses.py` (데이터 수집)
  - `sql/merge_market_data_daily_to_price_history.sql` (데이터 통합)
- **결론**: 핵심 테이블로 사용 중

## 4. 중복 및 차이점

### 중복되는 정보
- `timestamp`: 두 테이블 모두 타임스탬프 사용
- `crypto_id`: 두 테이블 모두 암호화폐 ID 사용
- `data_source`: 두 테이블 모두 데이터 출처 저장

### 차이점
1. **데이터 주기**: 
   - market_cap_data: 일일 또는 주기적
   - price_history: 1시간 단위

2. **데이터 내용**:
   - market_cap_data: 시가총액, 순위, 공급량 등 메타데이터
   - price_history: OHLC 가격, 거래량 등 가격 데이터

3. **업데이트 빈도**:
   - market_cap_data: 낮음
   - price_history: 높음

## 5. 통합 가능성 분석

### 통합 시 고려사항
1. **데이터 주기 차이**: 
   - market_cap_data는 일일 데이터
   - price_history는 1시간 데이터
   - 통합 시 NULL 값이 많아질 수 있음

2. **데이터 출처 차이**:
   - market_cap_data: CoinGecko, CoinMarketCap 등
   - price_history: Binance API
   - 출처가 다를 수 있음

3. **업데이트 빈도 차이**:
   - market_cap_data는 자주 업데이트되지 않음
   - price_history는 1시간마다 업데이트
   - 통합 시 불필요한 NULL 컬럼 증가

### 통합 방안
**옵션 1: price_history에 market_cap_data 컬럼 추가**
- 장점: 하나의 테이블로 관리
- 단점: 
  - 대부분의 레코드에서 market_cap 관련 컬럼이 NULL
  - 저장 공간 낭비
  - 쿼리 복잡도 증가

**옵션 2: 별도 테이블 유지 (권장)**
- 장점:
  - 각 테이블의 목적이 명확
  - 저장 공간 효율적
  - 쿼리 성능 유지
- 단점:
  - 두 테이블을 JOIN해야 시가총액과 가격을 함께 조회

**옵션 3: market_cap_data 삭제**
- 현재 사용되지 않으므로 삭제 고려 가능
- 단, 향후 시가총액 분석이 필요할 수 있으므로 보류 권장

## 6. 권장사항

### 현재 상황
- market_cap_data는 현재 사용되지 않음
- price_history는 핵심 테이블로 활발히 사용 중

### 권장 방안
1. **단기**: 두 테이블을 별도로 유지
   - 각 테이블의 목적이 다르므로 분리 유지
   - 필요시 JOIN으로 조회

2. **중기**: market_cap_data 사용 여부 재검토
   - 시가총액 분석이 필요한지 확인
   - 필요 없으면 삭제 고려

3. **장기**: 필요시 price_history에 선택적 컬럼 추가
   - 시가총액 정보가 자주 필요하면 price_history에 추가
   - 하지만 대부분 NULL이 될 수 있으므로 신중히 결정

## 7. 결론

- **market_cap_data**: 현재 사용되지 않지만, 시가총액 분석이 필요할 수 있으므로 보류
- **price_history**: 핵심 테이블로 계속 사용
- **통합**: 현재는 통합하지 않는 것을 권장 (목적이 다름)
- **향후**: 시가총액 분석이 필요하면 market_cap_data를 활용하거나, price_history에 선택적 컬럼 추가 검토

