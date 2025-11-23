#!/usr/bin/env python3
"""
whale_address 테이블의 name_tag를 실제 거래소/지갑 이름으로 업데이트하는 스크립트
Etherscan 및 BSCScan 웹 크롤링을 통해 실제 라벨(Name Tag)을 추출합니다.
Title 태그 파싱 방식을 주력으로 사용합니다.
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
load_dotenv(Path.cwd() / 'config' / '.env')

# Supabase 클라이언트 설정
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# 헤더 설정 (브라우저처럼 보이게 함)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://google.com',
    'Upgrade-Insecure-Requests': '1'
}

def extract_label_from_title(soup, address):
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
    
    # 라벨이 없는 경우 "Address 0x..." 형태로 시작함
    if first_part.lower().startswith('address'):
        return None
        
    # 라벨이 있는 경우
    return first_part

def get_real_label_etherscan(address):
    """Etherscan에서 실제 라벨 추출"""
    url = f"https://etherscan.io/address/{address}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Title 태그 파싱 (가장 확실)
        label = extract_label_from_title(soup, address)
        if label:
            return label
            
        # 2. 백업: spanLabelName
        name_tag_elem = soup.find('span', {'id': 'spanLabelName'})
        if name_tag_elem:
            return name_tag_elem.text.strip()
            
        return None
    except Exception as e:
        print(f"   ⚠️ Etherscan 크롤링 오류: {e}")
        return None

def get_real_label_bscscan(address):
    """BSCScan에서 실제 라벨 추출"""
    url = f"https://bscscan.com/address/{address}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Title 태그 파싱
        label = extract_label_from_title(soup, address)
        if label:
            return label
            
        # 2. 백업
        name_tag_elem = soup.find('span', {'id': 'spanLabelName'})
        if name_tag_elem:
            return name_tag_elem.text.strip()
            
        return None
    except Exception as e:
        print(f"   ⚠️ BSCScan 크롤링 오류: {e}")
        return None

def update_labels():
    print("=" * 80)
    print("🕵️‍♀️ 고래 지갑 실제 이름(Name Tag) 찾기 시작 (Title Parsing)")
    print("=" * 80)

    # 1. 업데이트 대상 조회 (일반적인 이름이거나 NULL인 경우)
    target_names = ['Ethereum', 'BNB', 'USDC', 'Bitcoin', 'Litecoin', 'Ripple', 'Unknown']
    
    # ETH 체인 조회
    print("\n1️⃣ ETH 및 USDC(ERC20) 주소 조회 중...")
    res_eth = supabase.table('whale_address')\
        .select('*')\
        .in_('chain_type', ['ETH', 'USDC'])\
        .execute()
        
    # BSC 체인 조회
    print("2️⃣ BSC 주소 조회 중...")
    res_bsc = supabase.table('whale_address')\
        .select('*')\
        .eq('chain_type', 'BSC')\
        .execute()

    targets = []
    
    # 필터링: 라벨이 일반적이거나 없는 경우만
    for row in res_eth.data:
        if not row['name_tag'] or row['name_tag'] in target_names:
            targets.append({'chain': 'ETH', 'address': row['address'], 'id': row['id']})
            
    for row in res_bsc.data:
        if not row['name_tag'] or row['name_tag'] in target_names:
            targets.append({'chain': 'BSC', 'address': row['address'], 'id': row['id']})
            
    print(f"\n📋 총 {len(targets)}개의 주소를 검사합니다.")
    
    updated_count = 0
    
    for i, target in enumerate(targets, 1):
        chain = target['chain']
        address = target['address']
        record_id = target['id']
        
        print(f"[{i}/{len(targets)}] {chain} {address[:10]}... ", end='', flush=True)
        
        real_label = None
        
        # 랜덤 대기 (차단 방지)
        time.sleep(random.uniform(1.0, 2.0))
        
        if chain == 'ETH':
            real_label = get_real_label_etherscan(address)
        elif chain == 'BSC':
            real_label = get_real_label_bscscan(address)
            
        if real_label:
            print(f"✅ 찾음: {real_label}")
            
            # DB 업데이트
            try:
                supabase.table('whale_address')\
                    .update({'name_tag': real_label})\
                    .eq('id', record_id)\
                    .execute()
                updated_count += 1
            except Exception as e:
                print(f"❌ 저장 실패: {e}")
        else:
            print("pass (라벨 없음)")
            
    print("\n" + "=" * 80)
    print(f"🎉 업데이트 완료: 총 {updated_count}개의 라벨을 찾아서 변경했습니다.")
    print("=" * 80)

if __name__ == "__main__":
    update_labels()
