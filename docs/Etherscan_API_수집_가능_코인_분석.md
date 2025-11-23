# 🔍 Etherscan API로 수집 가능한 코인 분석

## 📋 Etherscan이 지원하는 블록체인 네트워크

Etherscan API 키 하나로 다음 블록체인 네트워크의 데이터를 수집할 수 있습니다:

### ✅ 지원되는 주요 체인 (EVM 호환)

1. **Ethereum (ETH)** - https://etherscan.io
   - API: `https://api.etherscan.io/api`
   - 네이티브 코인: ETH
   - ERC-20 토큰: LINK, USDT, USDC 등

2. **Binance Smart Chain (BSC)** - https://bscscan.com
   - API: `https://api.bscscan.com/api`
   - 네이티브 코인: BNB
   - BEP-20 토큰

3. **Polygon (MATIC)** - https://polygonscan.com
   - API: `https://api.polygonscan.com/api`
   - 네이티브 코인: MATIC

4. **Avalanche (AVAX)** - https://snowtrace.io
   - API: `https://api.snowtrace.io/api`
   - 네이티브 코인: AVAX

5. **Fantom (FTM)** - https://ftmscan.com
   - API: `https://api.ftmscan.com/api`
   - 네이티브 코인: FTM

6. **Arbitrum** - https://arbiscan.io
   - API: `https://api.arbiscan.io/api`
   - L2 네트워크 (Ethereum)

7. **Optimism** - https://optimistic.etherscan.io
   - API: `https://api-optimistic.etherscan.io/api`
   - L2 네트워크 (Ethereum)

8. **Base** - https://basescan.org
   - API: `https://api.basescan.org/api`
   - L2 네트워크 (Coinbase)

9. **Linea** - https://lineascan.build
   - API: `https://api.lineascan.build/api`
   - L2 네트워크

10. **Scroll** - https://scrollscan.com
    - API: `https://api.scrollscan.com/api`
    - L2 네트워크

---

## 🐋 whale_address 테이블의 9개 코인 분석

### whale_address에 있는 코인 목록:
1. **BTC** (Bitcoin)
2. **ETH** (Ethereum)
3. **LTC** (Litecoin)
4. **DOGE** (Dogecoin)
5. **VTC** (Vertcoin)
6. **BSC** (Binance Coin / BNB)
7. **DOT** (Polkadot)
8. **LINK** (Chainlink)
9. **SOL** (Solana)

---

## ✅ Etherscan API로 수집 가능한 코인

### 1. **ETH (Ethereum)** ✅
- **체인**: Ethereum Mainnet
- **API 엔드포인트**: `https://api.etherscan.io/api`
- **수집 가능 데이터**:
  - 네이티브 ETH 거래 (ETH 전송)
  - ERC-20 토큰 거래 (LINK, USDT 등)
  - 스마트 컨트랙트 호출
- **whale_address**: ✅ ETH 체인의 고래 지갑 주소 거래 기록 수집 가능
- **whale_address 개수**: 300개

### 2. **BNB (BSC)** ✅
- **체인**: Binance Smart Chain
- **API 엔드포인트**: `https://api.bscscan.com/api`
- **수집 가능 데이터**:
  - 네이티브 BNB 거래 (BNB 전송)
  - BEP-20 토큰 거래
  - 스마트 컨트랙트 호출
- **whale_address**: ✅ BSC 체인의 고래 지갑 주소 거래 기록 수집 가능
- **whale_address 개수**: 100개
- **참고**: BSCScan도 같은 Etherscan 계정/API 키 사용

### 3. **LINK (Chainlink)** ✅
- **체인**: Ethereum Mainnet (ERC-20 토큰)
- **API 엔드포인트**: `https://api.etherscan.io/api`
- **수집 가능 데이터**:
  - LINK 토큰 전송 (ERC-20)
  - LINK 토큰 거래 내역
- **whale_address**: ✅ ETH 체인에서 LINK 토큰 거래 기록 수집 가능
- **whale_address 개수**: 100개
- **참고**: LINK는 Ethereum 네트워크의 ERC-20 토큰이므로 ETH 체인에서 수집

---

## ❌ Etherscan API로 수집 불가능한 코인

### 1. **BTC (Bitcoin)** ❌
- **이유**: Bitcoin은 자체 블록체인 네트워크 (UTXO 모델, EVM 비호환)
- **대안 API**:
  - BlockCypher API: `https://api.blockcypher.com/v1/btc/main`
  - Blockchain.info API: `https://blockchain.info/api`
  - Blockstream API: `https://blockstream.info/api`
- **whale_address 개수**: 300개

### 2. **LTC (Litecoin)** ❌
- **이유**: Litecoin은 자체 블록체인 네트워크 (UTXO 모델)
- **대안 API**:
  - BlockCypher API: `https://api.blockcypher.com/v1/ltc/main`
  - Litecoin Explorer API
- **whale_address 개수**: 300개

### 3. **DOGE (Dogecoin)** ❌
- **이유**: Dogecoin은 자체 블록체인 네트워크
- **대안 API**:
  - BlockCypher API: `https://api.blockcypher.com/v1/doge/main`
  - Dogechain Explorer
- **whale_address 개수**: 300개

### 4. **VTC (Vertcoin)** ❌
- **이유**: Vertcoin은 자체 블록체인 네트워크
- **대안 API**: Vertcoin Explorer API
- **whale_address 개수**: 300개

### 5. **DOT (Polkadot)** ❌
- **이유**: Polkadot은 Substrate 기반, EVM 호환 아님
- **대안 API**:
  - Polkadot Subscan API: `https://polkadot.api.subscan.io`
  - Polkadot.js API
- **whale_address 개수**: 100개

### 6. **SOL (Solana)** ❌
- **이유**: Solana는 자체 블록체인 네트워크 (Rust 기반, EVM 비호환)
- **대안 API**:
  - Solana RPC API: `https://api.mainnet-beta.solana.com`
  - Solscan API: `https://public-api.solscan.io`
- **whale_address 개수**: 100개

---

## 📊 수집 가능 여부 요약표

| 코인 | 체인 | Etherscan 지원 | 수집 가능 | API 엔드포인트 | whale_address 개수 |
|------|------|---------------|----------|---------------|-------------------|
| **ETH** | Ethereum | ✅ | ✅ **가능** | `api.etherscan.io` | 300개 |
| **BNB** | BSC | ✅ | ✅ **가능** | `api.bscscan.com` | 100개 |
| **LINK** | Ethereum (ERC-20) | ✅ | ✅ **가능** | `api.etherscan.io` | 100개 |
| **BTC** | Bitcoin | ❌ | ❌ 불가능 | - | 300개 |
| **LTC** | Litecoin | ❌ | ❌ 불가능 | - | 300개 |
| **DOGE** | Dogecoin | ❌ | ❌ 불가능 | - | 300개 |
| **VTC** | Vertcoin | ❌ | ❌ 불가능 | - | 300개 |
| **DOT** | Polkadot | ❌ | ❌ 불가능 | - | 100개 |
| **SOL** | Solana | ❌ | ❌ 불가능 | - | 100개 |

---

## 🎯 결론

### ✅ Etherscan API로 수집 가능한 코인: **3개**
1. **ETH** (Ethereum) - 300개 고래 지갑
2. **BNB** (BSC) - 100개 고래 지갑
3. **LINK** (Chainlink - Ethereum ERC-20) - 100개 고래 지갑

**총 수집 가능한 고래 지갑**: **500개** (전체 1,500개 중 33%)

### ❌ 추가 API가 필요한 코인: **6개**
1. **BTC** - 300개 (BlockCypher API 권장)
2. **LTC** - 300개 (BlockCypher API 권장)
3. **DOGE** - 300개 (BlockCypher API 권장)
4. **VTC** - 300개 (Vertcoin Explorer API)
5. **DOT** - 100개 (Polkadot Subscan API)
6. **SOL** - 100개 (Solana RPC API 또는 Solscan API)

**추가 API 필요 고래 지갑**: **1,000개** (전체 1,500개 중 67%)

---

## 💡 권장 작업 순서

### 1단계: Etherscan API로 수집 (현재 가능) ✅
- ETH: 300개 고래 지갑
- BNB: 100개 고래 지갑
- LINK: 100개 고래 지갑 (ERC-20 토큰 거래)
- **총 500개 고래 지갑의 거래 기록 수집 가능**

### 2단계: 추가 API 통합 (향후)
- Bitcoin 계열 (BTC, LTC, DOGE): BlockCypher API (무료 플랜 제공)
- Solana: Solana RPC API (무료) 또는 Solscan API
- Polkadot: Subscan API

---

## 🔧 스크립트 수정 필요사항

현재 `collect_whale_transactions_from_blockchain.py`는 ETH와 BSC만 지원합니다.

### 추가 필요 기능:
1. **LINK 토큰 거래 수집**
   - ERC-20 토큰 전송 이벤트 조회
   - LINK 컨트랙트 주소: `0x514910771AF9Ca656af840dff83E8264EcF986CA`
   - API 엔드포인트: `tokentx` (Token Transfer Events)

2. **다른 ERC-20 토큰 지원 확장**
   - USDT, USDC 등 다른 토큰도 수집 가능

---

## 📝 Etherscan API 사용 예시

### ETH 네이티브 거래 조회
```python
# 일반 거래 조회
url = "https://api.etherscan.io/api"
params = {
    'module': 'account',
    'action': 'txlist',
    'address': '0x...',
    'apikey': ETHERSCAN_API_KEY
}
```

### LINK 토큰 거래 조회 (ERC-20)
```python
# ERC-20 토큰 전송 이벤트 조회
url = "https://api.etherscan.io/api"
params = {
    'module': 'account',
    'action': 'tokentx',  # Token Transfer Events
    'contractaddress': '0x514910771AF9Ca656af840dff83E8264EcF986CA',  # LINK
    'address': '0x...',  # 고래 지갑 주소
    'apikey': ETHERSCAN_API_KEY
}
```

### BSC 거래 조회
```python
# BSC 거래 조회 (같은 API 키 사용)
url = "https://api.bscscan.com/api"
params = {
    'module': 'account',
    'action': 'txlist',
    'address': '0x...',
    'apikey': ETHERSCAN_API_KEY  # 같은 키 사용 가능
}
```

---

## ✅ 최종 요약

**Etherscan API 키 하나로 수집 가능한 코인:**
- ✅ ETH (Ethereum) - 300개 고래 지갑
- ✅ BNB (BSC) - 100개 고래 지갑  
- ✅ LINK (Chainlink) - 100개 고래 지갑

**총 500개 고래 지갑의 거래 기록을 수집할 수 있습니다!**



