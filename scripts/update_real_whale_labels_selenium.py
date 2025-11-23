#!/usr/bin/env python3
"""
Selenium을 이용한 Etherscan/BSCScan 라벨 크롤러
Cloudflare 및 JavaScript 차단을 우회하여 실제 라벨을 수집합니다.
"""

import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 환경 변수 로드
load_dotenv(Path.cwd() / 'config' / '.env')

# Supabase 설정
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

def setup_driver():
    """Chrome 드라이버 설정"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 화면 없이 실행
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_label_with_selenium(driver, chain, address):
    """Selenium으로 라벨 추출"""
    base_url = "https://etherscan.io" if chain == 'ETH' else "https://bscscan.com"
    url = f"{base_url}/address/{address}"
    
    try:
        print(f"   🌐 접속: {url}")
        driver.get(url)
        
        # Cloudflare 대기 (최대 10초)
        time.sleep(3) 
        
        # 1. Name Tag 찾기 (span#spanLabelName)
        try:
            label_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "spanLabelName"))
            )
            label = label_elem.text.strip()
            if label:
                return label
        except:
            pass
            
        # 2. Title에서 찾기 (백업)
        title = driver.title
        if '|' in title:
            label = title.split('|')[0].replace('Address', '').replace(address, '').strip()
            if label:
                return label
                
        return None
        
    except Exception as e:
        print(f"   ❌ 크롤링 오류: {e}")
        return None

def main():
    print("=" * 80)
    print("🕷️ Selenium 기반 고래 지갑 라벨 크롤러")
    print("=" * 80)
    
    driver = setup_driver()
    print("✅ Chrome Driver 로드 완료")
    
    # 업데이트 대상 조회 (일반적인 이름이거나 NULL인 경우)
    target_names = ['Ethereum', 'BNB', 'USDC', 'Bitcoin', 'Litecoin', 'Ripple', 'Unknown']
    
    # ETH 조회
    res_eth = supabase.table('whale_address')\
        .select('*')\
        .in_('chain_type', ['ETH', 'USDC'])\
        .execute()
    
    # BSC 조회
    res_bsc = supabase.table('whale_address')\
        .select('*')\
        .eq('chain_type', 'BSC')\
        .execute()
        
    targets = []
    for row in res_eth.data:
        if not row['name_tag'] or row['name_tag'] in target_names:
            targets.append({'chain': 'ETH', 'address': row['address'], 'id': row['id']})
    for row in res_bsc.data:
        if not row['name_tag'] or row['name_tag'] in target_names:
            targets.append({'chain': 'BSC', 'address': row['address'], 'id': row['id']})
            
    print(f"📋 총 {len(targets)}개의 주소를 검사합니다.")
    
    updated_count = 0
    
    try:
        for i, target in enumerate(targets, 1):
            chain = target['chain']
            address = target['address']
            
            print(f"[{i}/{len(targets)}] {chain} {address[:10]}... ", end='', flush=True)
            
            real_label = get_label_with_selenium(driver, chain, address)
            
            if real_label:
                print(f"✅ 찾음: {real_label}")
                supabase.table('whale_address')\
                    .update({'name_tag': real_label})\
                    .eq('id', target['id'])\
                    .execute()
                updated_count += 1
            else:
                print("pass (라벨 없음)")
                
            # 랜덤 대기
            time.sleep(random.uniform(2, 5))
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    finally:
        driver.quit()
        print(f"\n🎉 총 {updated_count}건 업데이트 완료")

if __name__ == "__main__":
    main()

