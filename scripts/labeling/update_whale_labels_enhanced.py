#!/usr/bin/env python3
"""
whale_address 테이블의 name_tag를 Etherscan/BSCScan에서 크롤링하여 보강
- 주소 축약형 (: 0x...), 코인명만 (BNB, ETH), NULL 등 무의미한 라벨 대상
"""

import os
import time
import random
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# 환경 변수 로드
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# Supabase 클라이언트
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# 무의미한 라벨 패턴
USELESS_PATTERNS = [
    'BNB', 'ETH', 'USDC', 'USDT', 'Ethereum', 'Bitcoin', 'Ripple', 
    'Unknown', 'Unknown Wallet', 'Litecoin', 'Dogecoin'
]


def is_useless_label(label):
    """무의미한 라벨인지 판단"""
    if not label:
        return True
    label = label.strip()
    # 주소 축약형
    if label.startswith(': 0x') or label.startswith('0x'):
        return True
    # 코인명만
    if label.upper() in [p.upper() for p in USELESS_PATTERNS]:
        return True
    # 너무 짧은 라벨
    if len(label) <= 4:
        return True
    # 숫자만
    if label.isdigit():
        return True
    return False


def extract_label_from_title(soup):
    """Title 태그에서 라벨 추출"""
    if not soup.title:
        return None
    
    title = soup.title.text.strip()
    # 형식: "Binance 7 | Address 0x... | Etherscan"
    # 형식: "Address 0x... | Etherscan" (라벨 없는 경우)
    
    if '|' not in title:
        return None
        
    parts = title.split('|')
    first_part = parts[0].strip()
    
    # 라벨이 없는 경우
    if first_part.lower().startswith('address'):
        return None
    if first_part.lower().startswith('contract'):
        return None
        
    return first_part


def get_label_etherscan(address):
    """Etherscan에서 라벨 추출"""
    url = f"https://etherscan.io/address/{address}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        label = extract_label_from_title(soup)
        return label
    except Exception as e:
        return None


def get_label_bscscan(address):
    """BSCScan에서 라벨 추출"""
    url = f"https://bscscan.com/address/{address}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        label = extract_label_from_title(soup)
        return label
    except Exception as e:
        return None


def update_labels_for_chain(chain_type, scan_func, limit=100):
    """특정 체인의 라벨 업데이트"""
    print(f"\n{'='*60}")
    print(f"📊 {chain_type} 체인 라벨 보강")
    print(f"{'='*60}")
    
    # 해당 체인의 주소 조회
    res = supabase.table('whale_address')\
        .select('id, address, name_tag')\
        .eq('chain_type', chain_type)\
        .limit(500)\
        .execute()
    
    if not res.data:
        print(f"   데이터 없음")
        return 0
    
    # 무의미한 라벨만 필터링
    targets = [r for r in res.data if is_useless_label(r.get('name_tag'))]
    print(f"   전체: {len(res.data)}건 / 보강 대상: {len(targets)}건")
    
    if not targets:
        print(f"   ✅ 보강 대상 없음")
        return 0
    
    # limit 적용
    targets = targets[:limit]
    print(f"   처리 대상: {len(targets)}건")
    
    updated = 0
    for i, t in enumerate(targets, 1):
        addr = t['address']
        old_label = t.get('name_tag', 'NULL')
        
        print(f"   [{i}/{len(targets)}] {addr[:12]}... ", end='', flush=True)
        
        # 크롤링
        new_label = scan_func(addr)
        
        if new_label and not is_useless_label(new_label):
            print(f"✅ {new_label[:30]}")
            
            # DB 업데이트
            try:
                supabase.table('whale_address')\
                    .update({'name_tag': new_label})\
                    .eq('id', t['id'])\
                    .execute()
                updated += 1
            except Exception as e:
                print(f"❌ 저장 실패")
        else:
            print(f"- (라벨 없음)")
        
        # Rate limit
        time.sleep(random.uniform(1.5, 2.5))
    
    print(f"\n   ✅ {updated}건 업데이트 완료")
    return updated


def main():
    print("=" * 80)
    print("🔧 whale_address 라벨 보강 작업")
    print("=" * 80)
    
    total_updated = 0
    
    # ETH 체인 (Etherscan)
    total_updated += update_labels_for_chain('ETH', get_label_etherscan, limit=50)
    
    # USDC 체인 (Etherscan - ERC20)
    total_updated += update_labels_for_chain('USDC', get_label_etherscan, limit=50)
    
    # BSC 체인 (BSCScan)
    total_updated += update_labels_for_chain('BSC', get_label_bscscan, limit=50)
    
    print("\n" + "=" * 80)
    print(f"🎉 총 {total_updated}건 라벨 보강 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()



