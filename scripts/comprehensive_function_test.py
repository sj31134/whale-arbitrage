#!/usr/bin/env python3
"""
DataLoader의 모든 함수를 테스트하는 종합 테스트
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

def test_all_data_loader_functions():
    """DataLoader의 모든 public 함수 테스트"""
    from data_loader import DataLoader
    
    print("="*80)
    print("DataLoader 모든 함수 테스트")
    print("="*80)
    
    loader = DataLoader()
    print(f"\n환경: {'로컬' if not loader.use_supabase else '클라우드 (Supabase)'}")
    
    results = {}
    
    # 1. get_available_dates
    print("\n[1] get_available_dates")
    for coin in ['BTC', 'ETH']:
        try:
            min_date, max_date = loader.get_available_dates(coin)
            if min_date and max_date:
                print(f"  ✅ {coin}: {min_date} ~ {max_date}")
                results[f'get_available_dates_{coin}'] = True
            else:
                print(f"  ❌ {coin}: None 반환")
                results[f'get_available_dates_{coin}'] = False
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'get_available_dates_{coin}'] = False
    
    # 2. get_available_dates_list
    print("\n[2] get_available_dates_list")
    for coin in ['BTC', 'ETH']:
        try:
            dates = loader.get_available_dates_list(coin)
            if len(dates) > 0:
                print(f"  ✅ {coin}: {len(dates)}개 날짜")
                results[f'get_available_dates_list_{coin}'] = True
            else:
                print(f"  ❌ {coin}: 빈 리스트")
                results[f'get_available_dates_list_{coin}'] = False
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'get_available_dates_list_{coin}'] = False
    
    # 3. check_date_available
    print("\n[3] check_date_available")
    for coin in ['BTC', 'ETH']:
        try:
            is_available, closest, diff = loader.check_date_available('2024-01-15', coin)
            print(f"  ✅ {coin}: available={is_available}, closest={closest}")
            results[f'check_date_available_{coin}'] = True
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'check_date_available_{coin}'] = False
    
    # 4. load_exchange_data
    print("\n[4] load_exchange_data")
    for coin in ['BTC', 'ETH']:
        try:
            df = loader.load_exchange_data('2024-01-01', '2024-01-10', coin)
            if len(df) > 0:
                print(f"  ✅ {coin}: {len(df)}행")
                results[f'load_exchange_data_{coin}'] = True
            else:
                print(f"  ⚠️ {coin}: 빈 DataFrame (데이터 없음)")
                results[f'load_exchange_data_{coin}'] = True  # 빈 DataFrame도 정상
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'load_exchange_data_{coin}'] = False
    
    # 5. validate_date_range
    print("\n[5] validate_date_range")
    for coin in ['BTC', 'ETH']:
        try:
            is_valid, msg = loader.validate_date_range('2024-01-01', '2024-01-31', coin)
            print(f"  ✅ {coin}: valid={is_valid}, msg={msg[:50] if msg else 'None'}")
            results[f'validate_date_range_{coin}'] = True
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'validate_date_range_{coin}'] = False
    
    # 6. load_risk_data
    print("\n[6] load_risk_data")
    for coin in ['BTC', 'ETH']:
        try:
            df = loader.load_risk_data('2024-01-01', '2024-01-31', coin)
            if len(df) > 0:
                print(f"  ✅ {coin}: {len(df)}행")
                results[f'load_risk_data_{coin}'] = True
            else:
                print(f"  ⚠️ {coin}: 빈 DataFrame")
                results[f'load_risk_data_{coin}'] = True
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'load_risk_data_{coin}'] = False
    
    # 7. load_futures_extended_metrics
    print("\n[7] load_futures_extended_metrics")
    for coin in ['BTC', 'ETH']:
        try:
            symbol = f"{coin}USDT"
            df = loader.load_futures_extended_metrics('2024-01-01', '2024-01-31', symbol)
            if len(df) > 0:
                print(f"  ✅ {coin}: {len(df)}행")
            else:
                print(f"  ⚠️ {coin}: 빈 DataFrame (선택적 데이터)")
            results[f'load_futures_extended_metrics_{coin}'] = True
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'load_futures_extended_metrics_{coin}'] = False
    
    # 8. load_risk_data_weekly
    print("\n[8] load_risk_data_weekly")
    for coin in ['BTC', 'ETH']:
        try:
            df = loader.load_risk_data_weekly('2024-01-01', '2024-01-31', coin)
            if len(df) > 0:
                print(f"  ✅ {coin}: {len(df)}행")
            else:
                print(f"  ⚠️ {coin}: 빈 DataFrame")
            results[f'load_risk_data_weekly_{coin}'] = True
        except Exception as e:
            print(f"  ❌ {coin}: {e}")
            results[f'load_risk_data_weekly_{coin}'] = False
    
    # 결과 요약
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    for test_name, result in sorted(results.items()):
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(test_all_data_loader_functions())

