#!/usr/bin/env python3
"""
CoinCarp에서 BNB 코인의 Rich List Top 100 고래 지갑 주소를 추출하여 CSV로 저장
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import time
from pathlib import Path

def extract_bnb_richlist():
    """BNB 코인의 Rich List Top 100 추출"""
    url = 'https://www.coincarp.com/ko/currencies/binance-coin/richlist/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    print("=" * 70)
    print("BNB 코인 Rich List Top 100 추출")
    print("=" * 70)
    print(f"\nURL: {url}")
    print("페이지 요청 중...")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✅ 응답 상태: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 방법 1: data-copy-text 속성에서 지갑 주소 추출
        copy_elements = soup.find_all(attrs={'data-copy-text': True})
        addresses_from_attr = []
        
        for elem in copy_elements:
            addr = elem.get('data-copy-text', '').strip()
            if addr and addr.startswith('0x') and len(addr) == 42:
                addresses_from_attr.append(addr)
        
        # 중복 제거
        addresses_from_attr = list(dict.fromkeys(addresses_from_attr))  # 순서 유지하면서 중복 제거
        
        print(f"\n[방법 1] data-copy-text 속성에서 추출: {len(addresses_from_attr)}개")
        
        # 방법 2: 정규표현식으로 지갑 주소 추출
        address_pattern = r'0x[a-fA-F0-9]{40}'
        addresses_from_regex = re.findall(address_pattern, response.text)
        addresses_from_regex = list(dict.fromkeys(addresses_from_regex))
        
        print(f"[방법 2] 정규표현식으로 추출: {len(addresses_from_regex)}개")
        
        # 방법 3: 테이블 행에서 직접 추출
        rows = soup.find_all('tr')
        addresses_from_table = []
        
        for row in rows:
            # td2 클래스를 가진 셀에서 주소 찾기
            td2 = row.find('td', class_='td2')
            if td2:
                # address-item 클래스 내의 span에서 주소 찾기
                address_item = td2.find('div', class_='address-item')
                if address_item:
                    span = address_item.find('span', class_='mr-2')
                    if span:
                        addr = span.get_text(strip=True)
                        if addr and addr.startswith('0x') and len(addr) == 42:
                            addresses_from_table.append(addr)
        
        addresses_from_table = list(dict.fromkeys(addresses_from_table))
        print(f"[방법 3] 테이블에서 직접 추출: {len(addresses_from_table)}개")
        
        # 모든 방법에서 주소 수집 (중복 제거 및 소문자 정규화)
        all_addresses = set()
        
        for addr in addresses_from_attr + addresses_from_regex + addresses_from_table:
            if addr and addr.startswith('0x') and len(addr) == 42:
                all_addresses.add(addr.lower())  # 소문자로 정규화하여 중복 제거
        
        # 리스트로 변환 (순서 유지)
        selected_addresses = list(all_addresses)[:100]  # Top 100만 선택
        
        print(f"\n✅ 최종 추출된 고유 주소: {len(selected_addresses)}개")
        
        if not selected_addresses:
            print("\n⚠️  지갑 주소를 찾을 수 없습니다.")
            print("\nHTML 구조 분석 중...")
            
            # 디버깅: 테이블 구조 확인
            table = soup.find('table')
            if table:
                print(f"테이블 발견: {len(table.find_all('tr'))}개 행")
            else:
                print("테이블을 찾을 수 없습니다.")
            
            # 스크립트 태그에서 데이터 찾기
            scripts = soup.find_all('script')
            print(f"\n스크립트 태그: {len(scripts)}개")
            for i, script in enumerate(scripts[:3]):
                if script.string:
                    if 'address' in script.string.lower() or '0x' in script.string:
                        print(f"\n스크립트 {i+1} 내용 (처음 500자):")
                        print(script.string[:500])
            
            return None
        
        return selected_addresses
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_to_csv(addresses, filename='bnb_richlist_top100.csv'):
    """지갑 주소를 CSV 파일로 저장"""
    if not addresses:
        print("저장할 주소가 없습니다.")
        return
    
    output_path = Path(__file__).parent / filename
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['rank', 'address', 'chain_type'])
        
        for rank, address in enumerate(addresses, 1):
            writer.writerow([rank, address, 'BSC'])
    
    print(f"\n✅ CSV 파일 저장 완료: {output_path}")
    print(f"   총 {len(addresses)}개의 지갑 주소 저장됨")
    
    return output_path

def main():
    """메인 함수"""
    addresses = extract_bnb_richlist()
    
    if addresses:
        output_path = save_to_csv(addresses)
        
        print("\n" + "=" * 70)
        print("✅ 작업 완료")
        print("=" * 70)
        print(f"\n📊 결과:")
        print(f"   - 추출된 주소 수: {len(addresses)}개")
        print(f"   - 저장 파일: {output_path}")
        print(f"\n샘플 주소 (최대 5개):")
        for i, addr in enumerate(addresses[:5], 1):
            print(f"   {i}. {addr}")
    else:
        print("\n❌ 주소 추출 실패")

if __name__ == '__main__':
    main()

