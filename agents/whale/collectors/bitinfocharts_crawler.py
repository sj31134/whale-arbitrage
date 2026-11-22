#!/usr/bin/env python3
"""
BitInfoCharts 크롤러
BTC, LTC, DOGE, XRP 등의 Rich List에서 지갑 라벨(거래소 등)을 수집합니다.
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

# Supabase 클라이언트
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

COIN_URLS = {
    'BTC': 'https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html',
    'LTC': 'https://bitinfocharts.com/top-100-richest-litecoin-addresses.html',
    'DOGE': 'https://bitinfocharts.com/top-100-richest-dogecoin-addresses.html',
    'XRP': 'https://bitinfocharts.com/top-100-richest-xrp-addresses.html',
    # 필요한 경우 추가
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

def crawl_bitinfocharts(coin_symbol):
    url = COIN_URLS.get(coin_symbol)
    if not url:
        print(f"❌ 지원하지 않는 코인: {coin_symbol}")
        return
    
    print(f"\n🕷️ BitInfoCharts 크롤링 시작: {coin_symbol}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ 요청 실패: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        
        print(f"   발견된 행 수: {len(rows)}")
        
        updated_count = 0
        
        for row in rows:
            # 링크 찾기
            links = row.find_all('a')
            for link in links:
                href = link.get('href')
                
                # 코인별 주소 URL 패턴 매칭
                # BTC: bitcoin/address/
                # LTC: litecoin/address/
                # DOGE: dogecoin/address/
                # XRP: xrp/address/
                path_segment = f"{coin_symbol.lower() if coin_symbol != 'BTC' else 'bitcoin'}/address/"
                if coin_symbol == 'BTC': path_segment = 'bitcoin/address/'
                elif coin_symbol == 'LTC': path_segment = 'litecoin/address/'
                elif coin_symbol == 'DOGE': path_segment = 'dogecoin/address/'
                elif coin_symbol == 'XRP': path_segment = 'xrp/address/'
                
                if href and path_segment in href:
                    address = href.split('/')[-1]
                    
                    # 라벨 찾기 (link 다음의 small 태그)
                    label_tag = link.find_next('small')
                    label = label_tag.text.strip() if label_tag else None
                    
                    # "wallet: " 접두사 제거
                    if label and label.startswith('wallet: '):
                        label = label.replace('wallet: ', '').strip()
                    
                    # 라벨이 없으면 건너뜀
                    if not label:
                        continue
                        
                    # Supabase 업데이트
                    try:
                        # 해당 주소가 존재하는지 확인
                        res = supabase.table('whale_address')\
                            .select('id')\
                            .eq('address', address)\
                            .execute()
                            
                        if res.data:
                            # 존재하면 업데이트
                            supabase.table('whale_address')\
                                .update({'name_tag': label})\
                                .eq('address', address)\
                                .execute()
                            print(f"   ✅ {coin_symbol} {address[:10]}... -> {label}")
                            updated_count += 1
                        else:
                            # 없으면... 일단 패스하거나, 필요시 추가 로직
                            # 여기서는 기존 whale_address에 있는 것만 업데이트한다고 가정
                            pass
                            
                    except Exception as e:
                        print(f"   ⚠️ 업데이트 실패 ({address}): {e}")
                        
        print(f"✅ {coin_symbol} 완료: {updated_count}건 업데이트됨")
        
    except Exception as e:
        print(f"❌ 크롤링 중 오류: {e}")

def main():
    print("=" * 80)
    print("🏗️ BitInfoCharts 지갑 라벨 수집기")
    print("=" * 80)
    
    target_coins = ['BTC', 'LTC', 'DOGE', 'XRP']
    
    for coin in target_coins:
        crawl_bitinfocharts(coin)
        time.sleep(random.uniform(2, 5)) # 딜레이

if __name__ == "__main__":
    main()

