#!/usr/bin/env python3
"""
CoinCarp에서 Litecoin과 Vertcoin의 Rich List 수집
"""

import os
import csv
import time
from pathlib import Path
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# Supabase 클라이언트 초기화
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# 코인 설정
COIN_CONFIGS = {
    'LTC': {
        'url_slug': 'litecoin',
        'chain_type': 'LTC',
        'name_tag': 'Litecoin',
        'csv_filename': 'ltc_mainnet_richlist_top100.csv'
    },
    'VTC': {
        'url_slug': 'vertcoin',
        'chain_type': 'VTC',
        'name_tag': 'Vertcoin',
        'csv_filename': 'vtc_mainnet_richlist_top100.csv'
    }
}

def scrape_richlist(url_slug: str, coin_symbol: str) -> List[str]:
    """CoinCarp에서 Rich List 주소 수집"""
    url = f"https://www.coincarp.com/ko/currencies/{url_slug}/richlist/"
    
    print(f"\n{'='*80}")
    print(f"🔍 {coin_symbol} Rich List 수집 시작")
    print(f"{'='*80}")
    print(f"URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 여러 방법으로 주소 추출 시도
        addresses = []
        
        # 방법 1: data-clipboard-text 속성에서 추출
        clipboard_elements = soup.find_all(attrs={'data-clipboard-text': True})
        for elem in clipboard_elements:
            addr = elem.get('data-clipboard-text', '').strip()
            if addr and len(addr) >= 20:  # 최소 길이 체크
                addresses.append(addr)
        
        # 방법 2: 테이블에서 주소 패턴 찾기
        table_rows = soup.find_all('tr')
        for row in table_rows:
            cells = row.find_all('td')
            for cell in cells:
                text = cell.get_text(strip=True)
                # LTC 주소는 L, M, 3로 시작하고 26-35자
                # VTC 주소는 V로 시작하고 약 34자
                if coin_symbol == 'LTC' and (text.startswith('L') or text.startswith('M') or text.startswith('3')):
                    if 26 <= len(text) <= 35:
                        addresses.append(text)
                elif coin_symbol == 'VTC' and text.startswith('V'):
                    if 30 <= len(text) <= 36:
                        addresses.append(text)
        
        # 중복 제거 및 소문자 정규화
        unique_addresses = list(dict.fromkeys(addresses))
        
        print(f"✅ 추출된 고유 주소: {len(unique_addresses)}개")
        
        # 상위 100개만 선택
        top_addresses = unique_addresses[:100]
        
        if top_addresses:
            print(f"📊 최종 선택: {len(top_addresses)}개 주소")
            print(f"📝 샘플 주소 (상위 3개):")
            for i, addr in enumerate(top_addresses[:3], 1):
                print(f"  {i}. {addr}")
        else:
            print("⚠️ 주소를 찾지 못했습니다.")
        
        return top_addresses
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []

def save_to_csv(addresses: List[str], filename: str, coin_symbol: str, chain_type: str) -> None:
    """Rich List를 CSV 파일로 저장"""
    csv_path = PROJECT_ROOT / filename
    
    print(f"\n💾 CSV 파일 저장: {filename}")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['rank', 'address', 'chain_type', 'coin_symbol', 'network'])
        
        for rank, address in enumerate(addresses, 1):
            writer.writerow([rank, address, chain_type, coin_symbol, 'mainnet'])
    
    print(f"✅ 저장 완료: {len(addresses)}건")

def upload_to_whale_address(csv_filename: str, chain_type: str, name_tag: str) -> None:
    """CSV 데이터를 whale_address 테이블에 업로드"""
    csv_path = PROJECT_ROOT / csv_filename
    
    print(f"\n{'='*80}")
    print(f"📤 whale_address 테이블 업로드: {chain_type}")
    print(f"{'='*80}")
    
    # CSV 읽기
    records = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rank = int(row['rank'])
            address = row['address']
            
            # whale_address 스키마에 맞게 변환
            record = {
                'id': f"{chain_type}{rank:03d}",
                'chain_type': chain_type,
                'address': address,
                'name_tag': name_tag,
                'balance': None,
                'percentage': None,
                'txn_count': None
            }
            records.append(record)
    
    print(f"📄 CSV 파일 읽기 완료: {len(records)}건")
    
    # Supabase에 업로드 (upsert)
    if records:
        try:
            # 배치로 업로드 (100건씩)
            batch_size = 100
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                response = supabase.table('whale_address').upsert(
                    batch,
                    on_conflict='id,chain_type'
                ).execute()
                print(f"  ✅ 배치 {i//batch_size + 1}: {len(batch)}건 업로드 완료")
            
            print(f"\n📊 총 업로드된 레코드: {len(records)}건")
            
        except Exception as e:
            print(f"❌ 업로드 실패: {e}")
    else:
        print("⚠️ 업로드할 데이터가 없습니다.")

def verify_upload(chain_type: str) -> None:
    """업로드 결과 검증"""
    print(f"\n{'='*80}")
    print(f"✅ 업로드 결과 검증: {chain_type}")
    print(f"{'='*80}")
    
    try:
        response = supabase.table('whale_address').select('*').eq('chain_type', chain_type).execute()
        
        data = response.data
        print(f"📊 {chain_type} 데이터: {len(data)}건")
        
        if data:
            print(f"\n📋 샘플 데이터 (상위 5건):")
            for i, record in enumerate(data[:5], 1):
                print(f"  [{i}] ID={record['id']}, Address={record['address'][:20]}..., name_tag={record['name_tag']}")
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")

def main():
    """메인 실행 함수"""
    print("\n" + "="*80)
    print("🐋 Litecoin & Vertcoin Rich List 수집 및 업로드")
    print("="*80)
    
    for coin_symbol, config in COIN_CONFIGS.items():
        print(f"\n{'#'*80}")
        print(f"# {coin_symbol} ({config['name_tag']}) 처리 시작")
        print(f"{'#'*80}")
        
        # Step 1: Rich List 수집
        addresses = scrape_richlist(config['url_slug'], coin_symbol)
        
        if not addresses:
            print(f"⚠️ {coin_symbol} 주소를 수집하지 못했습니다. 다음 코인으로 이동합니다.")
            continue
        
        # Step 2: CSV 저장
        save_to_csv(
            addresses,
            config['csv_filename'],
            coin_symbol,
            config['chain_type']
        )
        
        # Step 3: whale_address 업로드
        upload_to_whale_address(
            config['csv_filename'],
            config['chain_type'],
            config['name_tag']
        )
        
        # Step 4: 검증
        verify_upload(config['chain_type'])
        
        # 다음 코인 처리 전 대기
        if coin_symbol != list(COIN_CONFIGS.keys())[-1]:
            print(f"\n⏳ 다음 코인 처리 전 5초 대기...")
            time.sleep(5)
    
    print("\n" + "="*80)
    print("✅ 모든 작업 완료!")
    print("="*80)

if __name__ == "__main__":
    main()

