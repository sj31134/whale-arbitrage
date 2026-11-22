#!/usr/bin/env python3
"""
CoinCarp에서 BNB, USDC, XRP의 모든 네트워크별 Rich List Top 100 추출
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import time
from pathlib import Path
from typing import List, Dict, Optional

# 코인별 URL 매핑 및 네트워크 정보
COIN_CONFIGS = {
    'BNB': {
        'url_slug': 'binance-coin',
        'networks': ['mainnet'],  # BNB는 메인넷만
        'chain_type': 'BSC'
    },
    'USDC': {
        'url_slug': 'usdc',
        'networks': ['ethereum', 'bsc', 'polygon', 'arbitrum', 'optimism', 'avalanche', 'solana', 'base'],  # USDC는 여러 네트워크
        'chain_type': 'USDC'  # 네트워크별로 체인 타입이 다를 수 있음
    },
    'XRP': {
        'url_slug': 'ripple',
        'networks': ['mainnet'],  # XRP는 XRP Ledger 메인넷만
        'chain_type': 'XRP'
    }
}

def extract_richlist_from_url(url: str, coin_symbol: str, network: str) -> Optional[List[str]]:
    """
    CoinCarp URL에서 Rich List 추출
    
    Parameters:
    -----------
    url : str
        CoinCarp Rich List URL
    coin_symbol : str
        코인 심볼 (BNB, USDC, XRP)
    network : str
        네트워크 이름
    
    Returns:
    --------
    List[str] : 지갑 주소 리스트 (최대 100개)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        print(f"   📥 페이지 요청 중...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 방법 1: data-copy-text 속성에서 지갑 주소 추출
        copy_elements = soup.find_all(attrs={'data-copy-text': True})
        addresses_from_attr = []
        
        for elem in copy_elements:
            addr = elem.get('data-copy-text', '').strip()
            if addr and addr.startswith('0x') and len(addr) == 42:
                addresses_from_attr.append(addr)
        
        addresses_from_attr = list(dict.fromkeys(addresses_from_attr))
        
        # 방법 2: 정규표현식으로 지갑 주소 추출
        address_pattern = r'0x[a-fA-F0-9]{40}'
        addresses_from_regex = re.findall(address_pattern, response.text)
        addresses_from_regex = list(dict.fromkeys(addresses_from_regex))
        
        # 방법 3: 테이블 행에서 직접 추출
        rows = soup.find_all('tr')
        addresses_from_table = []
        
        for row in rows:
            td2 = row.find('td', class_='td2')
            if td2:
                address_item = td2.find('div', class_='address-item')
                if address_item:
                    span = address_item.find('span', class_='mr-2')
                    if span:
                        addr = span.get_text(strip=True)
                        if addr and addr.startswith('0x') and len(addr) == 42:
                            addresses_from_table.append(addr)
        
        addresses_from_table = list(dict.fromkeys(addresses_from_table))
        
        # XRP의 경우 주소 형식이 다를 수 있음 (r로 시작)
        if coin_symbol == 'XRP':
            xrp_pattern = r'r[1-9A-HJ-NP-Za-km-z]{25,34}'
            xrp_addresses = re.findall(xrp_pattern, response.text)
            addresses_from_regex.extend(xrp_addresses)
        
        # 모든 방법에서 주소 수집 (중복 제거 및 소문자 정규화)
        all_addresses = set()
        
        for addr in addresses_from_attr + addresses_from_regex + addresses_from_table:
            if addr:
                # 이더리움/BSC 주소 (0x로 시작, 42자리)
                if addr.startswith('0x') and len(addr) == 42:
                    all_addresses.add(addr.lower())
                # XRP 주소 (r로 시작)
                elif coin_symbol == 'XRP' and addr.startswith('r') and len(addr) >= 25:
                    all_addresses.add(addr)
        
        # 리스트로 변환하고 Top 100만 선택
        selected_addresses = list(all_addresses)[:100]
        
        if selected_addresses:
            print(f"   ✅ {len(selected_addresses)}개 주소 추출 완료")
            return selected_addresses
        else:
            print(f"   ⚠️  주소를 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")
        return None

def get_network_url(base_slug: str, network: str) -> str:
    """
    네트워크별 URL 생성
    
    Parameters:
    -----------
    base_slug : str
        코인 URL slug (예: 'binance-coin')
    network : str
        네트워크 이름
    
    Returns:
    --------
    str : 완전한 URL
    """
    base_url = f"https://www.coincarp.com/ko/currencies/{base_slug}/richlist/"
    
    if network == 'mainnet':
        return base_url
    else:
        # 네트워크별로 ?platform= 파라미터 추가
        return f"{base_url}?platform={network}"

def save_to_csv(addresses: List[str], filename: str, coin_symbol: str, network: str, chain_type: str):
    """지갑 주소를 CSV 파일로 저장"""
    if not addresses:
        return None
    
    output_path = Path(__file__).parent / filename
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['rank', 'address', 'chain_type', 'coin_symbol', 'network'])
        
        for rank, address in enumerate(addresses, 1):
            writer.writerow([rank, address, chain_type, coin_symbol, network])
    
    return output_path

def collect_all_richlists():
    """모든 코인과 네트워크의 Rich List 수집"""
    print("=" * 70)
    print("CoinCarp Rich List 수집 (BNB, USDC, XRP)")
    print("=" * 70)
    
    results = {}
    
    for coin_symbol, config in COIN_CONFIGS.items():
        print(f"\n[{coin_symbol}] Rich List 수집 시작")
        print("-" * 70)
        
        coin_results = {}
        
        for network in config['networks']:
            print(f"\n  네트워크: {network}")
            
            url = get_network_url(config['url_slug'], network)
            print(f"  URL: {url}")
            
            addresses = extract_richlist_from_url(url, coin_symbol, network)
            
            if addresses:
                # 파일명 생성
                filename = f"{coin_symbol.lower()}_{network}_richlist_top100.csv"
                
                # 체인 타입 결정
                if coin_symbol == 'USDC':
                    # USDC는 네트워크에 따라 체인 타입이 다름
                    chain_mapping = {
                        'ethereum': 'ETH',
                        'bsc': 'BSC',
                        'polygon': 'POLYGON',
                        'arbitrum': 'ARBITRUM',
                        'optimism': 'OPTIMISM',
                        'avalanche': 'AVALANCHE',
                        'solana': 'SOL',
                        'base': 'BASE'
                    }
                    chain_type = chain_mapping.get(network, 'USDC')
                else:
                    chain_type = config['chain_type']
                
                output_path = save_to_csv(addresses, filename, coin_symbol, network, chain_type)
                
                coin_results[network] = {
                    'count': len(addresses),
                    'file': str(output_path),
                    'status': 'success'
                }
                
                print(f"  ✅ 저장 완료: {output_path}")
            else:
                coin_results[network] = {
                    'count': 0,
                    'file': None,
                    'status': 'failed'
                }
            
            # Rate limiting
            time.sleep(1)
        
        results[coin_symbol] = coin_results
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("✅ 수집 완료")
    print("=" * 70)
    
    total_files = 0
    total_addresses = 0
    
    for coin_symbol, coin_results in results.items():
        print(f"\n[{coin_symbol}]")
        for network, result in coin_results.items():
            if result['status'] == 'success':
                print(f"  - {network}: {result['count']}개 주소 → {result['file']}")
                total_files += 1
                total_addresses += result['count']
            else:
                print(f"  - {network}: 실패")
    
    print(f"\n📊 전체 통계:")
    print(f"   - 생성된 CSV 파일: {total_files}개")
    print(f"   - 총 추출된 주소: {total_addresses}개")
    
    return results

def main():
    """메인 함수"""
    try:
        results = collect_all_richlists()
        
        print("\n" + "=" * 70)
        print("✅ 모든 작업 완료")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

