#!/usr/bin/env python3
"""
MOVE 거래를 세분화하여 더 의미 있는 라벨로 분류
- WALLET_TRANSFER: 개인 지갑 간 이동 (고래 축적/분산 추정)
- DEFI_INTERACT: DeFi 프로토콜 상호작용
- BRIDGE: 브릿지를 통한 크로스체인 이동
- STAKING: 스테이킹/예치
- CONTRACT_CALL: 기타 컨트랙트 호출
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import time

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# 거래소 키워드
EXCHANGE_KEYWORDS = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 'gate', 'bybit', 'kucoin', 'upbit', 'bithumb', 'bittrex', 'gemini', 'crypto.com', 'exchange', 'htx', 'mexc', 'bitget', 'bitstamp', 'poloniex', 'ftx', 'robinhood']

# DeFi 프로토콜 키워드
DEFI_KEYWORDS = ['uniswap', 'sushiswap', 'pancake', 'curve', 'aave', 'compound', 'maker', 'yearn', 'balancer', 'dydx', '1inch', 'paraswap', 'kyber', 'bancor', 'convex', 'frax', 'lido', 'rocket pool', 'synthetix', 'tornado', 'pool', 'swap', 'router', 'vault']

# 브릿지 키워드
BRIDGE_KEYWORDS = ['bridge', 'l1', 'l2', 'linea', 'arbitrum', 'optimism', 'polygon', 'mantle', 'zksync', 'starknet', 'base', 'scroll', 'portal', 'cross', 'wormhole', 'multichain', 'stargate', 'hop', 'across', 'celer', 'layerzero']

# 스테이킹 키워드
STAKING_KEYWORDS = ['staking', 'stake', 'beacon', 'deposit', 'validator', 'withdrawal', 'eth2', 'lido', 'rocket']

# 컨트랙트 키워드
CONTRACT_KEYWORDS = ['contract', 'proxy', 'implementation', 'factory', 'registry', 'controller', 'manager']

# 수수료/마이너 키워드
FEE_KEYWORDS = ['fee', 'miner', 'coinbase', 'flashbots', 'mev', 'recipient']


def classify_move(from_label, to_label):
    """MOVE 거래를 세분화 분류"""
    from_l = (from_label or '').lower()
    to_l = (to_label or '').lower()
    
    # 1. 거래소 관련 (BUY/SELL로 재분류)
    from_is_ex = any(kw in from_l for kw in EXCHANGE_KEYWORDS)
    to_is_ex = any(kw in to_l for kw in EXCHANGE_KEYWORDS)
    
    if from_is_ex and not to_is_ex:
        return 'BUY'  # 거래소→개인
    if not from_is_ex and to_is_ex:
        return 'SELL'  # 개인→거래소
    if from_is_ex and to_is_ex:
        return 'EXCHANGE_TRANSFER'  # 거래소→거래소
    
    # 2. 브릿지 (크로스체인)
    if any(kw in to_l for kw in BRIDGE_KEYWORDS):
        return 'BRIDGE_OUT'  # 다른 체인으로 이동
    if any(kw in from_l for kw in BRIDGE_KEYWORDS):
        return 'BRIDGE_IN'  # 다른 체인에서 유입
    
    # 3. 스테이킹
    if any(kw in to_l for kw in STAKING_KEYWORDS):
        return 'STAKING'  # 스테이킹/예치
    
    # 4. DeFi 프로토콜
    if any(kw in to_l for kw in DEFI_KEYWORDS) or any(kw in from_l for kw in DEFI_KEYWORDS):
        return 'DEFI'  # DeFi 상호작용
    
    # 5. 수수료/마이너
    if any(kw in to_l for kw in FEE_KEYWORDS):
        return 'FEE'  # 수수료 지불
    
    # 6. 컨트랙트 호출
    if any(kw in to_l for kw in CONTRACT_KEYWORDS):
        return 'CONTRACT'  # 컨트랙트 상호작용
    
    # 7. 개인 지갑 간 이동 (Unknown Wallet 포함)
    if from_label in ['Unknown Wallet', None, ''] or to_label in ['Unknown Wallet', None, '']:
        return 'WALLET_TRANSFER'  # 지갑 간 이동
    
    # 8. 기타
    return 'OTHER'


def refine_move_labels():
    """MOVE 거래 세분화"""
    print("=" * 80)
    print("📊 MOVE 거래 세분화 라벨링")
    print("=" * 80)
    
    batch_size = 500
    total_processed = 0
    stats = {}
    batch_num = 0
    
    while True:
        batch_num += 1
        
        # MOVE 거래 조회
        batch = supabase.table('whale_transactions')\
            .select('id, from_label, to_label')\
            .eq('transaction_direction', 'MOVE')\
            .limit(batch_size)\
            .execute()
        
        if not batch.data:
            break
        
        # 분류
        updates = {}
        for row in batch.data:
            new_label = classify_move(row.get('from_label'), row.get('to_label'))
            if new_label not in updates:
                updates[new_label] = []
            updates[new_label].append(row['id'])
            
            if new_label not in stats:
                stats[new_label] = 0
            stats[new_label] += 1
        
        # 업데이트
        for label, ids in updates.items():
            if label == 'MOVE':  # 변경 없음
                continue
            for i in range(0, len(ids), 100):
                try:
                    supabase.table('whale_transactions')\
                        .update({'transaction_direction': label})\
                        .in_('id', ids[i:i+100])\
                        .execute()
                except:
                    pass
        
        total_processed += len(batch.data)
        print(f"   배치 {batch_num}: {len(batch.data)}건 처리")
        
        # 변경 없는 배치가 계속되면 중단
        if all(label == 'MOVE' or label == 'OTHER' or label == 'WALLET_TRANSFER' for label in updates.keys()):
            if batch_num > 5:
                break
        
        time.sleep(0.1)
    
    print(f"\n✅ 총 {total_processed}건 처리")
    print("\n📊 분류 결과:")
    for label, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {label}: {cnt}건")
    
    return stats


def main():
    stats = refine_move_labels()
    
    # 최종 분포 확인
    print("\n" + "=" * 80)
    print("📊 최종 transaction_direction 분포")
    print("=" * 80)
    
    # 각 유형별 카운트
    labels = ['BUY', 'SELL', 'MOVE', 'BRIDGE_OUT', 'BRIDGE_IN', 'STAKING', 'DEFI', 'FEE', 'CONTRACT', 'WALLET_TRANSFER', 'EXCHANGE_TRANSFER', 'OTHER']
    
    for label in labels:
        try:
            res = supabase.table('whale_transactions').select('id', count='exact').eq('transaction_direction', label).limit(1).execute()
            if res.count > 0:
                print(f"   {label}: {res.count:,}건")
        except:
            pass


if __name__ == "__main__":
    main()



