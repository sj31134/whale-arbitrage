# 🔍 BNB, USDC, XRP 거래 기록 수집 가능성 검토

## 📊 현재 설정된 API 키 현황

| API | 상태 | 사용 가능 체인 |
|-----|------|---------------|
| ETHERSCAN_API_KEY | ✅ 설정됨 | Ethereum, BSC (BSCScan) |
| BSCSCAN_API_KEY | ❌ 미설정 | BSC (Etherscan 키로 대체 가능) |
| SOCHAIN_API_KEY | ❌ 미설정 | BTC, LTC, DOGE |
| SUBSCAN_API_KEY | ✅ 설정됨 | Polkadot (DOT) |
| SOLSCAN_API_KEY | ✅ 설정됨 | Solana (SOL) |

---

## 1️⃣ BNB (Binance Coin) 거래 기록 수집

### ✅ 수집 가능

**현재 상태:**
- `whale_address` 테이블에 **BSC 체인 주소 100개** 존재
- 코드에 이미 구현됨 (`collect_all_whale_transactions.py`)

**수집 방식:**
- **체인**: Binance Smart Chain (BSC)
- **API**: BSCScan API (Etherscan API 키 사용 가능)
- **엔드포인트**: `https://api.bscscan.com/api`
- **코드 위치**: `src/collectors/multi_chain_collector.py` → `fetch_etherscan_transactions(addresses, 'bsc', api_key)`

**수집 가능 데이터:**
- ✅ 네이티브 BNB 거래 (BNB 전송)
- ✅ BEP-20 토큰 거래 (USDC-BSC 포함)

**실행 방법:**
```python
# collect_all_whale_transactions.py 실행 시 자동으로 수집됨
# 또는
fetch_etherscan_transactions(whale_addresses['bsc'], 'bsc', ETHERSCAN_API_KEY)
```

---

## 2️⃣ USDC (USD Coin) 거래 기록 수집

### ⚠️ 부분적으로 수집 가능 (네트워크별로 다름)

**현재 상태:**
- `whale_address` 테이블에 **USDC 주소 없음**
- 하지만 `collect_all_coincarp_richlist.py`로 수집한 CSV 파일들 존재:
  - `usdc_ethereum_richlist_top100.csv`
  - `usdc_bsc_richlist_top100.csv`
  - `usdc_polygon_richlist_top100.csv`
  - `usdc_arbitrum_richlist_top100.csv`
  - `usdc_optimism_richlist_top100.csv`
  - `usdc_avalanche_richlist_top100.csv`
  - `usdc_solana_richlist_top100.csv`
  - `usdc_base_richlist_top100.csv`

**USDC는 여러 네트워크에 존재:**
1. **Ethereum** ✅ 수집 가능
   - **API**: Etherscan API
   - **토큰 타입**: ERC-20
   - **컨트랙트 주소**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
   - **현재 API 키**: ✅ ETHERSCAN_API_KEY 설정됨
   - **코드 구현**: ⚠️ 토큰 거래 수집 기능 필요 (LINK와 유사한 방식)

2. **BSC (Binance Smart Chain)** ✅ 수집 가능
   - **API**: BSCScan API (Etherscan API 키 사용)
   - **토큰 타입**: BEP-20
   - **컨트랙트 주소**: `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d`
   - **현재 API 키**: ✅ ETHERSCAN_API_KEY로 가능
   - **코드 구현**: ⚠️ 토큰 거래 수집 기능 필요

3. **Polygon** ⚠️ 수집 가능 (API 키 필요)
   - **API**: PolygonScan API
   - **토큰 타입**: ERC-20 (Polygon)
   - **컨트랙트 주소**: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
   - **현재 API 키**: ❌ POLYGONSCAN_API_KEY 미설정
   - **대안**: Etherscan 계정으로 PolygonScan API 키 발급 가능

4. **Arbitrum** ⚠️ 수집 가능 (API 키 필요)
   - **API**: Arbiscan API
   - **토큰 타입**: ERC-20 (Arbitrum)
   - **컨트랙트 주소**: `0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8`
   - **현재 API 키**: ❌ ARBISCAN_API_KEY 미설정
   - **대안**: Etherscan 계정으로 Arbiscan API 키 발급 가능

5. **Optimism** ⚠️ 수집 가능 (API 키 필요)
   - **API**: Optimistic Etherscan API
   - **토큰 타입**: ERC-20 (Optimism)
   - **컨트랙트 주소**: `0x7F5c764cBc14f9669B88837ca1490cCa17c31607`
   - **현재 API 키**: ❌ OPTIMISM_API_KEY 미설정
   - **대안**: Etherscan 계정으로 Optimism API 키 발급 가능

6. **Avalanche** ⚠️ 수집 가능 (API 키 필요)
   - **API**: SnowTrace API
   - **토큰 타입**: ERC-20 (Avalanche)
   - **컨트랙트 주소**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
   - **현재 API 키**: ❌ SNOWTRACE_API_KEY 미설정
   - **대안**: Etherscan 계정으로 SnowTrace API 키 발급 가능

7. **Solana** ✅ 수집 가능
   - **API**: Solscan API
   - **토큰 타입**: SPL Token
   - **컨트랙트 주소**: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (Mint Address)
   - **현재 API 키**: ✅ SOLSCAN_API_KEY 설정됨
   - **코드 구현**: ⚠️ Solana 토큰 거래 수집 기능 필요

8. **Base** ⚠️ 수집 가능 (API 키 필요)
   - **API**: BaseScan API
   - **토큰 타입**: ERC-20 (Base)
   - **컨트랙트 주소**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
   - **현재 API 키**: ❌ BASESCAN_API_KEY 미설정
   - **대안**: Etherscan 계정으로 BaseScan API 키 발급 가능

**필요한 작업:**
1. ✅ Ethereum, BSC: 토큰 거래 수집 함수 구현 (LINK와 유사)
2. ⚠️ Solana: SPL 토큰 거래 수집 함수 구현
3. ❌ 기타 네트워크: API 키 발급 및 수집 함수 구현

---

## 3️⃣ XRP (Ripple) 거래 기록 수집

### ❌ 현재 수집 불가능 (API 구현 필요)

**현재 상태:**
- `whale_address` 테이블에 **XRP 주소 없음**
- 하지만 `xrp_mainnet_richlist_top100.csv` 파일 존재

**XRP Ledger 특성:**
- **체인**: XRP Ledger (자체 블록체인)
- **주소 형식**: `r...` (예: `rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH`)
- **API**: XRPScan API 또는 XRP Ledger Public API

**사용 가능한 API:**
1. **XRPScan API** (추천)
   - **URL**: `https://api.xrpscan.com/api/v1/account/{address}/transactions`
   - **API 키**: 무료 (제한적), 유료 플랜 있음
   - **문서**: https://xrpscan.com/api

2. **XRP Ledger Public API**
   - **URL**: `https://s1.ripple.com:51234/` (JSON-RPC)
   - **API 키**: 불필요 (공개 API)
   - **문서**: https://xrpl.org/docs.html

3. **Bithomp API**
   - **URL**: `https://bithomp.com/api/v2/address/{address}`
   - **API 키**: 무료 (제한적)

**필요한 작업:**
1. ❌ XRP Ledger 거래 수집 함수 구현 (`fetch_xrpscan_transactions` 또는 `fetch_xrpledger_transactions`)
2. ❌ `collect_all_whale_transactions.py`에 XRP 수집 로직 추가
3. ⚠️ XRP 주소를 `whale_address` 테이블에 추가 (CSV에서 import)

---

## 📋 종합 요약

| 코인 | 네트워크 | 수집 가능 여부 | 현재 API 키 | 코드 구현 | 주소 존재 |
|------|---------|--------------|-----------|----------|----------|
| **BNB** | BSC | ✅ **가능** | ✅ ETHERSCAN_API_KEY | ✅ 구현됨 | ✅ 100개 |
| **USDC** | Ethereum | ✅ **가능** | ✅ ETHERSCAN_API_KEY | ⚠️ 구현 필요 | ❌ 없음 |
| **USDC** | BSC | ✅ **가능** | ✅ ETHERSCAN_API_KEY | ⚠️ 구현 필요 | ❌ 없음 |
| **USDC** | Solana | ✅ **가능** | ✅ SOLSCAN_API_KEY | ⚠️ 구현 필요 | ❌ 없음 |
| **USDC** | Polygon | ⚠️ **부분 가능** | ❌ 미설정 | ❌ 구현 필요 | ❌ 없음 |
| **USDC** | Arbitrum | ⚠️ **부분 가능** | ❌ 미설정 | ❌ 구현 필요 | ❌ 없음 |
| **USDC** | Optimism | ⚠️ **부분 가능** | ❌ 미설정 | ❌ 구현 필요 | ❌ 없음 |
| **USDC** | Avalanche | ⚠️ **부분 가능** | ❌ 미설정 | ❌ 구현 필요 | ❌ 없음 |
| **USDC** | Base | ⚠️ **부분 가능** | ❌ 미설정 | ❌ 구현 필요 | ❌ 없음 |
| **XRP** | XRP Ledger | ❌ **불가능** | ❌ 미설정 | ❌ 구현 필요 | ❌ 없음 |

---

## 🚀 즉시 수집 가능한 코인

### 1. BNB (BSC)
- ✅ **즉시 수집 가능**
- `collect_all_whale_transactions.py` 실행 시 자동으로 수집됨

### 2. USDC (Ethereum, BSC)
- ⚠️ **코드 구현 후 수집 가능**
- LINK 토큰 수집 방식과 유사하게 구현 필요
- USDC 컨트랙트 주소로 토큰 거래 조회

### 3. USDC (Solana)
- ⚠️ **코드 구현 후 수집 가능**
- Solscan API로 SPL 토큰 거래 조회 필요

---

## 📝 다음 단계 권장사항

1. **BNB**: 이미 수집 가능하므로 바로 실행
2. **USDC (Ethereum, BSC)**: 토큰 거래 수집 함수 구현 (우선순위 높음)
3. **USDC (Solana)**: Solscan API로 SPL 토큰 거래 수집 구현
4. **XRP**: XRPScan API 통합 및 수집 함수 구현
5. **USDC 기타 네트워크**: 필요 시 API 키 발급 및 구현

