# 📊 Whale Tracking System - DB 구조 분석 요약

## 🎯 목표
1. **데이터 수집**: 고래 주소 → 거래기록 → 고래별 거래기록
2. **SNS 포스트**: 레딧, 트위터 → 인플루언서의 포스트
3. **데이터 분석**: 코인 가격(상승/하락) vs 고래 거래(매수/매도) + 인플루언서 감정(긍정/부정)
4. **프론트 서비스**: 코인별 영향도 순위를 지도에 표시

---

## ✅ 현재 존재하는 테이블 (12개)

| 테이블명 | 목적 | 상태 | 목표 달성도 |
|---------|------|------|-----------|
| `cryptocurrencies` | 암호화폐 기본 정보 | ✅ 존재 | 필요 (코인 정보) |
| `whale_address` | 고래 지갑 주소 | ✅ 존재 | 필요 (고래 주소) |
| `whale_transactions` | 고래 거래 기록 | ✅ 존재 | 부분적 (매수/매도 구분 필요) |
| `internal_transactions` | 내부 거래 | ✅ 존재 | 보조 데이터 |
| `influencer` | 인플루언서 포스트 | ✅ 존재 | 필요 (감정 분석 포함) |
| `market_cap_data` | 시가총액 데이터 | ✅ 존재 | 보조 데이터 |
| `market_data_daily` | 일일 시장 데이터 | ✅ 존재 | 보조 데이터 |
| `price_history` | 가격 이력 | ✅ 존재 | 필요 (가격 변동 분석) |
| `news_sentiment` | 뉴스 감정 분석 | ✅ 존재 | 보조 데이터 |
| `reddit_sentiment` | 레딧 감정 분석 | ✅ 존재 | 필요 (SNS 감정) |
| `social_data` | 소셜 미디어 데이터 | ✅ 존재 | 필요 (트위터 포함) |
| `prediction_accuracy` | 예측 정확도 | ✅ 존재 | 보조 데이터 |

---

## ❌ 추가해야 할 테이블 (5개)

### 🔴 필수 테이블 (4개)

#### 1. `whale_transaction_analysis`
- **목적**: 고래별 거래 분석 (매수/매도 구분)
- **필수도**: 높음
- **주요 컬럼**:
  - `id` (PK)
  - `whale_address_id` (FK → whale_address)
  - `tx_hash` (FK → whale_transactions)
  - `transaction_type` (매수/매도)
  - `amount_usd`
  - `timestamp`
  - `coin_symbol`

#### 2. `price_movement`
- **목적**: 가격 변동 분석 (상승/하락)
- **필수도**: 높음
- **주요 컬럼**:
  - `id` (PK)
  - `crypto_id` (FK → cryptocurrencies)
  - `timestamp`
  - `price_change_percent`
  - `movement_type` (상승/하락)
  - `time_window` (1h, 24h, 7d 등)

#### 3. `correlation_analysis`
- **목적**: 상관 분석 결과 저장
- **필수도**: 높음
- **주요 컬럼**:
  - `id` (PK)
  - `crypto_id` (FK → cryptocurrencies)
  - `analysis_date`
  - `whale_transaction_correlation`
  - `influencer_sentiment_correlation`
  - `reddit_sentiment_correlation`
  - `twitter_sentiment_correlation`
  - `combined_correlation_score`

#### 4. `coin_influence_ranking`
- **목적**: 코인별 영향도 순위 (프론트 표시용)
- **필수도**: 높음
- **주요 컬럼**:
  - `id` (PK)
  - `crypto_id` (FK → cryptocurrencies)
  - `ranking_date`
  - `whale_influence_score`
  - `influencer_influence_score`
  - `social_influence_score`
  - `total_influence_score`
  - `rank`

### 🟡 선택 테이블 (1개)

#### 5. `twitter_sentiment`
- **목적**: 트위터 감정 분석 (별도 테이블)
- **필수도**: 중간
- **주요 컬럼**:
  - `id` (PK)
  - `crypto_id` (FK → cryptocurrencies)
  - `timestamp`
  - `tweet_count`
  - `sentiment_score`
  - `positive_count`
  - `negative_count`
  - `neutral_count`

---

## 📈 데이터 흐름

### 1. 고래 거래 데이터 흐름
```
whale_address → whale_transactions → whale_transaction_analysis
(고래 주소) → (거래 기록) → (매수/매도 분석)
```

### 2. SNS 감정 데이터 흐름
```
influencer → (감정 분석)
reddit_sentiment → (레딧 감정)
twitter_sentiment → (트위터 감정)
```

### 3. 가격 변동 데이터 흐름
```
price_history → price_movement
(가격 이력) → (상승/하락 분석)
```

### 4. 상관 분석 데이터 흐름
```
whale_transaction_analysis + influencer + price_movement
→ correlation_analysis → coin_influence_ranking
```

---

## 🔗 주요 관계 (Foreign Keys)

| 자식 테이블 | 자식 컬럼 | 부모 테이블 | 부모 컬럼 |
|-----------|---------|-----------|---------|
| `whale_transaction_analysis` | `whale_address_id` | `whale_address` | `id` |
| `whale_transaction_analysis` | `tx_hash` | `whale_transactions` | `tx_hash` |
| `price_movement` | `crypto_id` | `cryptocurrencies` | `id` |
| `correlation_analysis` | `crypto_id` | `cryptocurrencies` | `id` |
| `coin_influence_ranking` | `crypto_id` | `cryptocurrencies` | `id` |
| `twitter_sentiment` | `crypto_id` | `cryptocurrencies` | `id` |

---

## 🎯 목표 달성 체크리스트

### ✅ 현재 완료
- [x] 고래 주소 수집 (whale_address)
- [x] 고래 거래 기록 수집 (whale_transactions)
- [x] 인플루언서 포스트 수집 (influencer)
- [x] 레딧 감정 분석 (reddit_sentiment)
- [x] 가격 이력 수집 (price_history)

### ❌ 추가 필요
- [ ] 고래별 거래 분석 테이블 (whale_transaction_analysis)
- [ ] 가격 변동 분석 테이블 (price_movement)
- [ ] 트위터 감정 분석 테이블 (twitter_sentiment)
- [ ] 상관 분석 테이블 (correlation_analysis)
- [ ] 코인 영향도 순위 테이블 (coin_influence_ranking)

---

## 📝 다음 단계

1. **추가 테이블 생성**: 5개 테이블의 SQL 스키마 작성 및 실행
2. **데이터 파이프라인 구축**: 
   - whale_transactions → whale_transaction_analysis (매수/매도 구분)
   - price_history → price_movement (상승/하락 구분)
3. **분석 로직 구현**:
   - 상관 분석 알고리즘
   - 영향도 점수 계산
4. **프론트 연동**: coin_influence_ranking 데이터를 지도에 표시



