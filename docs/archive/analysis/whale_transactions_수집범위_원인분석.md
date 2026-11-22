# whale_transactions 수집 범위 제한 원인 분석

## 📊 현재 상황

### whale_address 테이블
- **총 레코드**: 1,000건
- **체인 종류**: 5개
  - BSC: 100건
  - BTC: 300건
  - DOGE: 300건
  - DOT: 100건
  - ETH: 200건

### whale_transactions 테이블
- **총 거래 레코드**: 1,000건
- **수집된 coin_symbol**: **2개만** (ETH, LINK)
  - **LINK**: 696건
  - **ETH**: 304건
- **chain**: ethereum만 (1,000건)

### 문제점
사용자가 언급한 'ETH, LINK, DOT, BSC, USDC' 5개 코인 중, 실제로는 **ETH와 LINK 2개만** 수집되어 있음.

---

## 🔍 근본 원인 분석

### 1. **제한적인 스크립트 실행**

#### 실행된 스크립트: `collect_whale_transactions_from_blockchain.py`
- **지원 코인**: ETH, BNB (BSC), LINK
- **실제 수집**: ETH, LINK만
- **문제**: BSC는 whale_address에 있지만 실제 거래가 수집되지 않음

```python
# collect_whale_transactions_from_blockchain.py의 supported_chains
supported_chains = {
    'ETH': {
        'chain_name': 'ethereum',
        'coin_symbol': 'ETH',
        'fetch_native': lambda addr, key: fetch_ethereum_transactions(addr, key),
        'fetch_token': lambda addr, key: fetch_ethereum_token_transactions(addr, LINK_CONTRACT_ADDRESS, key),
        'api_key': ETHERSCAN_API_KEY,
    },
    'BSC': {
        'chain_name': 'bsc',
        'coin_symbol': 'BNB',
        'fetch_native': lambda addr, key: fetch_bsc_transactions(addr, key),
        'api_key': BSCSCAN_API_KEY,  # ❌ 미설정
    }
}
```

#### 실행되지 않은 스크립트들
1. **`collect_all_whale_transactions.py`**
   - 지원: ETH, BNB, LINK, BTC, LTC, DOGE, DOT, SOL, VTC
   - 상태: 실행 안됨 또는 일부만 실행
   
2. **`collect_bnb_usdc_xrp_transactions_2025_may_june.py`**
   - 지원: BNB, USDC, XRP
   - 상태: 실행되었으나 2025년 7-8월 데이터만 수집 (거래 0건 또는 매우 적음)

---

### 2. **API 키 부족**

| API 키 | 상태 | 필요한 코인 |
|--------|------|------------|
| **ETHERSCAN_API_KEY** | ✅ 설정됨 | ETH, LINK |
| **BSCSCAN_API_KEY** | ❌ 미설정 | BNB (BSC) |
| **SOCHAIN_API_KEY** | ❌ 미설정 | BTC, LTC, DOGE |
| **SUBSCAN_API_KEY** | ✅ 설정됨 | DOT |
| **SOLSCAN_API_KEY** | ✅ 설정됨 | SOL |
| **POLYGONSCAN_API_KEY** | ❌ 미설정 | POLYGON |

**결과**:
- BSCSCAN_API_KEY 미설정 → BSC 거래 수집 불가
- SOCHAIN_API_KEY 미설정 → BTC, LTC, DOGE 수집 불가

---

### 3. **날짜 범위 제한**

`collect_bnb_usdc_xrp_transactions_2025_may_june.py`:
- 수집 기간: 2025년 5-6월, 7-8월만
- 문제: 미래 날짜이거나 해당 기간에 거래가 없으면 데이터 없음
- 결과: USDC, XRP는 거래가 거의 없거나 0건

---

### 4. **체인별 수집 로직 차이**

#### whale_address에 있는 체인 vs 수집 가능한 체인

| chain_type | 예상 coin_symbol | 수집 가능 여부 | 이유 |
|------------|-----------------|---------------|------|
| **ETH** | ETH | ✅ 수집됨 | ETHERSCAN_API_KEY 있음 |
| **LINK** | LINK | ✅ 수집됨 | ETHERSCAN_API_KEY (토큰) |
| **BSC** | BNB (또는 BSC) | ❌ 수집 안됨 | BSCSCAN_API_KEY 없음 |
| **BTC** | BTC | ❌ 수집 안됨 | SOCHAIN_API_KEY 없음 또는 스크립트 미실행 |
| **DOGE** | DOGE | ❌ 수집 안됨 | SOCHAIN_API_KEY 없음 또는 스크립트 미실행 |
| **DOT** | DOT | ❌ 수집 안됨 | SUBSCAN_API_KEY 있으나 스크립트 미실행 |

---

### 5. **coin_symbol 매핑 불일치**

```python
# whale_address.chain_type → whale_transactions.coin_symbol 매핑
- chain_type='BSC' → coin_symbol='BNB' (예상)
- 하지만 일부 스크립트는 'BSC'로 저장
- 혼란 발생
```

**실제 수집된 데이터**:
- chain='ethereum'만 (1,000건)
- coin_symbol='ETH' (304건), 'LINK' (696건)

---

## 📋 왜 5개 코인이 아닌 2개만 수집되었나?

### 수집된 코인: ETH, LINK

**이유**:
1. `collect_whale_transactions_from_blockchain.py` 스크립트만 실행됨
2. ETHERSCAN_API_KEY만 설정되어 있음
3. ETH 네이티브 거래 + LINK 토큰 거래 수집
4. whale_address의 ETH chain_type (200건) 주소로 거래 수집

### 수집되지 않은 코인

#### 1. **BSC (BNB)**
- whale_address에 100건 있음
- **원인**: BSCSCAN_API_KEY 미설정
- **결과**: 수집 불가

#### 2. **DOT**
- whale_address에 100건 있음
- **원인**: SUBSCAN_API_KEY는 있으나 `collect_all_whale_transactions.py` 미실행
- **결과**: 수집 안됨

#### 3. **USDC**
- `collect_bnb_usdc_xrp_transactions_2025_may_june.py` 실행됨
- **원인**: 2025년 7-8월 데이터만 수집 시도 (미래 날짜 또는 거래 없음)
- **결과**: 거래 0건 또는 매우 적음

#### 4. **BTC, DOGE**
- whale_address에 각 300건 있음
- **원인**: SOCHAIN_API_KEY 미설정
- **결과**: 수집 불가

---

## ✅ 최종 결론

### 2개 코인만 수집된 근본 원인

1. **단일 스크립트만 실행**: `collect_whale_transactions_from_blockchain.py`만 실행
2. **단일 API 키만 설정**: ETHERSCAN_API_KEY만 있음
3. **제한적인 지원 범위**: 해당 스크립트는 ETH와 LINK만 지원
4. **다른 스크립트 미실행**: 
   - `collect_all_whale_transactions.py` 미실행
   - BTC, LTC, DOGE, DOT, SOL, VTC 수집 안됨

### 수집 가능했으나 안된 코인

| 코인 | whale_address | 필요 API | 상태 | 차단 이유 |
|------|--------------|----------|------|-----------|
| BNB (BSC) | 100건 | BSCSCAN | ❌ | API 키 없음 |
| DOT | 100건 | SUBSCAN | ✅ | 스크립트 미실행 |
| BTC | 300건 | SOCHAIN | ❌ | API 키 없음 |
| DOGE | 300건 | SOCHAIN | ❌ | API 키 없음 |

---

## 💡 권장 조치 (참고만)

### 1. API 키 추가
- BSCSCAN_API_KEY 설정 → BSC 수집 가능
- SOCHAIN_API_KEY 설정 → BTC, LTC, DOGE 수집 가능

### 2. 스크립트 실행
- `collect_all_whale_transactions.py` 실행 → 모든 코인 수집

### 3. 날짜 범위 조정
- `collect_bnb_usdc_xrp_transactions_2025_may_june.py`의 날짜를 과거로 변경
- 또는 전체 거래 수집으로 변경

---

## 📊 데이터 흐름 다이어그램

```
whale_address (1,000건)
├─ ETH (200건) ──────────┐
├─ BSC (100건) ─────X────┤  ETHERSCAN_API_KEY
├─ BTC (300건) ─────X    │         ↓
├─ DOGE (300건) ────X    └─→ collect_whale_transactions_from_blockchain.py
└─ DOT (100건) ─────X              ↓
                             whale_transactions (1,000건)
   X = 수집 안됨               ├─ ETH: 304건
                              └─ LINK: 696건
```

---

## 🎯 핵심 요약

**왜 2개 코인만 수집되었는가?**

1. **실행된 스크립트**: `collect_whale_transactions_from_blockchain.py`만
2. **설정된 API 키**: ETHERSCAN_API_KEY만
3. **지원되는 코인**: ETH, LINK만
4. **결과**: 1,000건 모두 ethereum 체인의 ETH/LINK 거래

**나머지 코인들은?**
- BSC, BTC, DOGE, DOT: API 키 없음 또는 스크립트 미실행
- USDC, XRP: 날짜 범위 제한으로 거래 없음

