# 🔍 Etherscan API 지원 체인 분석

## 📋 Etherscan이 지원하는 블록체인 네트워크

Etherscan API 키 하나로 다음 블록체인 네트워크의 데이터를 수집할 수 있습니다:

### ✅ 지원되는 주요 체인

1. **Ethereum (ETH)** - https://etherscan.io
   - 네이티브 코인: ETH
   - ERC-20 토큰: LINK, USDT, USDC 등

2. **Binance Smart Chain (BSC)** - https://bscscan.com
   - 네이티브 코인: BNB
   - BEP-20 토큰

3. **Polygon (MATIC)** - https://polygonscan.com
   - 네이티브 코인: MATIC
   - ERC-20 토큰

4. **Avalanche (AVAX)** - https://snowtrace.io
   - 네이티브 코인: AVAX
   - ERC-20 토큰

5. **Fantom (FTM)** - https://ftmscan.com
   - 네이티브 코인: FTM

6. **Arbitrum** - https://arbiscan.io
   - L2 네트워크 (Ethereum)

7. **Optimism** - https://optimistic.etherscan.io
   - L2 네트워크 (Ethereum)

8. **Base** - https://basescan.org
   - L2 네트워크 (Coinbase)

9. **Linea** - https://lineascan.build
   - L2 네트워크

10. **Scroll** - https://scrollscan.com
    - L2 네트워크

---

## 🐋 whale_address 테이블의 코인 분석

### whale_address에 있는 9개 코인:
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
- **수집 가능**: 네이티브 ETH 거래 + ERC-20 토큰 거래
- **whale_address**: ETH 체인의 고래 지갑 주소 거래 기록 수집 가능

### 2. **BNB (BSC)** ✅
- **체인**: Binance Smart Chain
- **API 엔드포인트**: `https://api.bscscan.com/api`
- **수집 가능**: 네이티브 BNB 거래 + BEP-20 토큰 거래
- **whale_address**: BSC 체인의 고래 지갑 주소 거래 기록 수집 가능
- **참고**: BSCScan도 같은 Etherscan 계정 사용

### 3. **LINK (Chainlink)** ✅ (간접)
- **체인**: Ethereum Mainnet (ERC-20 토큰)
- **API 엔드포인트**: `https://api.etherscan.io/api`
- **수집 가능**: LINK 토큰 거래 (ERC-20)
- **whale_address**: ETH 체인에서 LINK 토큰 거래 기록 수집 가능
- **참고**: LINK는 Ethereum 네트워크의 ERC-20 토큰

---

## ❌ Etherscan API로 수집 불가능한 코인

### 1. **BTC (Bitcoin)** ❌
- **이유**: Bitcoin은 자체 블록체인 네트워크 (UTXO 모델)
- **대안**: BlockCypher API, Blockchain.info API, Blockstream API

### 2. **LTC (Litecoin)** ❌
- **이유**: Litecoin은 자체 블록체인 네트워크
- **대안**: BlockCypher API, Litecoin Explorer API

### 3. **DOGE (Dogecoin)** ❌
- **이유**: Dogecoin은 자체 블록체인 네트워크
- **대안**: BlockCypher API, Dogechain Explorer

### 4. **VTC (Vertcoin)** ❌
- **이유**: Vertcoin은 자체 블록체인 네트워크
- **대안**: Vertcoin Explorer API

### 5. **DOT (Polkadot)** ❌
- **이유**: Polkadot은 Substrate 기반, EVM 호환 아님
- **대안**: Polkadot Subscan API

### 6. **SOL (Solana)** ❌
- **이유**: Solana는 자체 블록체인 네트워크 (Rust 기반)
- **대안**: Solana RPC API, Solscan API

---

## 📊 수집 가능 여부 요약

| 코인 | 체인 | Etherscan 지원 | 수집 가능 여부 | API 엔드포인트 |
|------|------|---------------|--------------|---------------|
| **ETH** | Ethereum | ✅ | ✅ **가능** | `api.etherscan.io` |
| **BNB** | BSC | ✅ | ✅ **가능** | `api.bscscan.com` |
| **LINK** | Ethereum (ERC-20) | ✅ | ✅ **가능** | `api.etherscan.io` |
| **BTC** | Bitcoin | ❌ | ❌ 불가능 | - |
| **LTC** | Litecoin | ❌ | ❌ 불가능 | - |
| **DOGE** | Dogecoin | ❌ | ❌ 불가능 | - |
| **VTC** | Vertcoin | ❌ | ❌ 불가능 | - |
| **DOT** | Polkadot | ❌ | ❌ 불가능 | - |
| **SOL** | Solana | ❌ | ❌ 불가능 | - |

---

## 🎯 결론

### Etherscan API로 수집 가능한 코인: **3개**
1. ✅ **ETH** (Ethereum)
2. ✅ **BNB** (BSC)
3. ✅ **LINK** (Chainlink - Ethereum ERC-20)

### 추가 API가 필요한 코인: **6개**
1. ❌ **BTC** - BlockCypher API 또는 Blockchain.info API
2. ❌ **LTC** - BlockCypher API
3. ❌ **DOGE** - BlockCypher API
4. ❌ **VTC** - Vertcoin Explorer API
5. ❌ **DOT** - Polkadot Subscan API
6. ❌ **SOL** - Solana RPC API 또는 Solscan API

---

## 💡 권장 사항

### 1단계: Etherscan API로 수집 (현재 가능)
- ETH, BNB, LINK 거래 기록 수집
- `collect_whale_transactions_from_blockchain.py` 수정 필요

### 2단계: 추가 API 통합 (향후)
- Bitcoin 계열 (BTC, LTC, DOGE): BlockCypher API
- Solana: Solana RPC API
- Polkadot: Subscan API

---

## 🔧 스크립트 수정 필요사항

현재 `collect_whale_transactions_from_blockchain.py`는 ETH와 BSC만 지원합니다.
LINK 토큰 거래도 수집하려면 ERC-20 토큰 거래 조회 기능을 추가해야 합니다.



