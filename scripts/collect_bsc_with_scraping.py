#!/usr/bin/env python3
"""
BSC 데이터 웹 스크래핑을 통한 수집
API 오류 시 웹 크롤링으로 거래 데이터 수집
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# BSC 하이브리드 컬렉터 임포트
from scripts.collectors.bsc_hybrid_collector import (
    get_supabase_client,
    get_bsc_whale_addresses,
    collect_transactions_for_address,
    scrape_high_value_transactions
)

def collect_bsc_with_scraping():
    """BSC 데이터를 웹 스크래핑으로 수집"""
    print("=" * 80)
    print("🟡 BSC 거래 데이터 웹 스크래핑 수집")
    print("=" * 80)
    
    START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    END_DATE = datetime.now(timezone.utc)
    
    print(f"\n수집 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    
    try:
        supabase = get_supabase_client()
        
        # BSC 고래 주소 조회
        addresses = get_bsc_whale_addresses(supabase)
        print(f"\n📋 BSC 고래 주소: {len(addresses)}개")
        
        total_collected = 0
        total_scraped = 0
        
        for idx, addr_info in enumerate(addresses, 1):
            address = addr_info['address']
            name_tag = addr_info.get('name_tag', 'Unknown')
            
            print(f"\n[{idx}/{len(addresses)}] {name_tag} ({address[:10]}...)")
            
            # 1단계: API로 거래 수집 시도
            print("  📊 API 수집 시도...")
            collected = collect_transactions_for_address(
                supabase, 
                address, 
                name_tag, 
                START_DATE, 
                END_DATE
            )
            
            if collected > 0:
                total_collected += collected
                print(f"  ✅ API로 {collected}건 수집")
            else:
                print("  ⚠️ API 수집 실패, 웹 스크래핑 시도...")
                
                # 2단계: 웹 스크래핑으로 수집
                scraped = scrape_high_value_transactions(
                    supabase,
                    address,
                    name_tag,
                    min_bnb=100,  # 100 BNB 이상
                    start_date=START_DATE,
                    end_date=END_DATE
                )
                
                if scraped > 0:
                    total_scraped += scraped
                    print(f"  ✅ 웹 스크래핑으로 {scraped}건 수집")
                else:
                    print(f"  ❌ 수집 실패")
        
        print("\n" + "=" * 80)
        print("✅ BSC 수집 완료")
        print("=" * 80)
        print(f"\nAPI 수집: {total_collected}건")
        print(f"웹 스크래핑: {total_scraped}건")
        print(f"총 수집: {total_collected + total_scraped}건")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    collect_bsc_with_scraping()

