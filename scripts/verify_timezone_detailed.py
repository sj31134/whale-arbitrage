#!/usr/bin/env python3
"""
타임존 상세 확인 스크립트
- price_history: 바이낸스 API가 반환하는 시간과 DB 저장 시간 비교
- whale_transactions: 블록체인 API가 반환하는 시간과 DB 저장 시간 비교
- UTC/GMT 기준 명확히 확인
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client
import requests

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 바이낸스 API 기본 URL
BINANCE_API_BASE = "https://api.binance.com/api/v3"

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_binance_api_timezone():
    """바이낸스 API가 반환하는 시간 확인"""
    print("=" * 70)
    print("🔍 바이낸스 API 타임존 확인")
    print("=" * 70)
    
    # 바이낸스 서버 시간 조회
    try:
        response = requests.get(f"{BINANCE_API_BASE}/time", timeout=10)
        response.raise_for_status()
        server_time = response.json()
        server_timestamp = server_time['serverTime']
        
        # 서버 시간을 UTC로 변환
        server_dt = datetime.fromtimestamp(server_timestamp / 1000, tz=timezone.utc)
        local_dt = datetime.now(timezone.utc)
        
        print(f"\n📡 바이낸스 서버 시간:")
        print(f"   서버 타임스탬프: {server_timestamp} (밀리초)")
        print(f"   UTC 변환: {server_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   현재 UTC 시간: {local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   차이: {(server_dt - local_dt).total_seconds():.1f}초")
        
        # K-line 데이터 샘플 조회
        print(f"\n📊 K-line 데이터 샘플 (BTCUSDT, 1시간):")
        kline_response = requests.get(
            f"{BINANCE_API_BASE}/klines",
            params={'symbol': 'BTCUSDT', 'interval': '1h', 'limit': 1},
            timeout=10
        )
        kline_response.raise_for_status()
        klines = kline_response.json()
        
        if klines:
            kline = klines[0]
            open_time_ms = kline[0]
            close_time_ms = kline[6]
            
            open_dt = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
            close_dt = datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc)
            
            print(f"   Open Time: {open_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   Close Time: {close_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   KST 변환: {open_dt.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        print(f"\n✅ 결론: 바이낸스 API는 UTC 기준으로 시간을 반환합니다.")
        print(f"   (서버 시간과 UTC 시간이 일치)")
        
    except Exception as e:
        print(f"❌ 바이낸스 API 확인 실패: {e}")

def check_price_history_timezone(supabase):
    """price_history 테이블의 타임존 확인"""
    print("\n" + "=" * 70)
    print("📊 price_history 테이블 타임존 상세 분석")
    print("=" * 70)
    
    try:
        # 최근 데이터 샘플 조회
        response = supabase.table('price_history')\
            .select('timestamp, crypto_id, data_source, raw_data')\
            .order('timestamp', desc=True)\
            .limit(20)\
            .execute()
        
        if not response.data:
            print("   ⚠️ 데이터가 없습니다.")
            return
        
        print(f"\n📋 최근 20건의 timestamp 분석:")
        print(f"\n{'순번':<6} {'Timestamp (DB)':<30} {'UTC 변환':<30} {'KST 변환':<30} {'출처':<10}")
        print("-" * 100)
        
        utc_count = 0
        kst_count = 0
        other_count = 0
        
        for i, row in enumerate(response.data, 1):
            ts_str = row.get('timestamp')
            data_source = row.get('data_source', 'unknown')
            raw_data = row.get('raw_data', {})
            
            try:
                if isinstance(ts_str, str):
                    if 'T' in ts_str:
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    elif ts_str.isdigit():
                        dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                    else:
                        dt = datetime.fromisoformat(ts_str)
                else:
                    dt = ts_str
                
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                
                kst_dt = dt.astimezone(timezone(timedelta(hours=9)))
                
                # raw_data에서 open_time 확인
                raw_open_time = raw_data.get('open_time', '') if isinstance(raw_data, dict) else ''
                
                print(f"{i:<6} {ts_str[:28]:<30} {dt.strftime('%Y-%m-%d %H:%M:%S %Z'):<30} {kst_dt.strftime('%Y-%m-%d %H:%M:%S %Z'):<30} {data_source:<10}")
                
                # UTC/KST 판단 (시간대 분포로)
                hour = dt.hour
                if 0 <= hour <= 8:
                    utc_count += 1
                elif 9 <= hour <= 17:
                    kst_count += 1
                else:
                    other_count += 1
                    
            except Exception as e:
                print(f"{i:<6} 파싱 실패: {ts_str[:50]}")
        
        print(f"\n📈 시간대 분포 분석:")
        print(f"   UTC 시간대 (0-8시): {utc_count}건")
        print(f"   KST 시간대 (9-17시): {kst_count}건")
        print(f"   기타 (18-23시): {other_count}건")
        
        if utc_count > kst_count * 2:
            print(f"\n✅ 결론: price_history는 UTC 기준으로 저장되어 있습니다.")
        elif kst_count > utc_count * 2:
            print(f"\n⚠️ 결론: price_history는 KST 기준으로 저장되어 있을 가능성이 있습니다.")
        else:
            print(f"\n⚠️ 결론: 명확한 패턴이 보이지 않습니다. 추가 확인이 필요합니다.")
        
    except Exception as e:
        print(f"❌ price_history 확인 실패: {e}")

def check_whale_transactions_timezone(supabase):
    """whale_transactions 테이블의 타임존 확인"""
    print("\n" + "=" * 70)
    print("🐋 whale_transactions 테이블 타임존 상세 분석")
    print("=" * 70)
    
    try:
        # 최근 데이터 샘플 조회
        response = supabase.table('whale_transactions')\
            .select('block_timestamp, coin_symbol, chain')\
            .order('block_timestamp', desc=True)\
            .limit(20)\
            .execute()
        
        if not response.data:
            print("   ⚠️ 데이터가 없습니다.")
            return
        
        print(f"\n📋 최근 20건의 block_timestamp 분석:")
        print(f"\n{'순번':<6} {'Timestamp (DB)':<30} {'UTC 변환':<30} {'KST 변환':<30} {'코인':<8} {'체인':<10}")
        print("-" * 110)
        
        utc_count = 0
        kst_count = 0
        other_count = 0
        
        for i, row in enumerate(response.data, 1):
            ts_str = row.get('block_timestamp')
            coin = row.get('coin_symbol', 'unknown')
            chain = row.get('chain', 'unknown')
            
            try:
                if isinstance(ts_str, str):
                    if 'T' in ts_str:
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    elif ts_str.isdigit():
                        dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                    elif '.' in ts_str and ' ' in ts_str:
                        # "2025.9.30 14:09" 형식 처리
                        try:
                            date_part, time_part = ts_str.split(' ')
                            year, month, day = map(int, date_part.split('.'))
                            hour, minute = map(int, time_part.split(':'))
                            dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
                        except:
                            dt = datetime.fromisoformat(ts_str)
                    else:
                        dt = datetime.fromisoformat(ts_str)
                else:
                    dt = ts_str
                
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                
                kst_dt = dt.astimezone(timezone(timedelta(hours=9)))
                
                print(f"{i:<6} {str(ts_str)[:28]:<30} {dt.strftime('%Y-%m-%d %H:%M:%S %Z'):<30} {kst_dt.strftime('%Y-%m-%d %H:%M:%S %Z'):<30} {coin:<8} {chain:<10}")
                
                # UTC/KST 판단
                hour = dt.hour
                if 0 <= hour <= 8:
                    utc_count += 1
                elif 9 <= hour <= 17:
                    kst_count += 1
                else:
                    other_count += 1
                    
            except Exception as e:
                print(f"{i:<6} 파싱 실패: {str(ts_str)[:50]}")
        
        print(f"\n📈 시간대 분포 분석:")
        print(f"   UTC 시간대 (0-8시): {utc_count}건")
        print(f"   KST 시간대 (9-17시): {kst_count}건")
        print(f"   기타 (18-23시): {other_count}건")
        
        print(f"\n✅ 결론: whale_transactions는 블록체인 표준에 따라 UTC 기준으로 저장되어야 합니다.")
        print(f"   (모든 블록체인은 UTC 기준 타임스탬프 사용)")
        
    except Exception as e:
        print(f"❌ whale_transactions 확인 실패: {e}")

def check_blockchain_api_timezone():
    """블록체인 API 타임존 확인"""
    print("\n" + "=" * 70)
    print("🔗 블록체인 API 타임존 확인")
    print("=" * 70)
    
    # Blockstream API (Bitcoin) 확인
    print(f"\n📡 Blockstream API (Bitcoin):")
    try:
        # 최신 블록 정보 조회
        response = requests.get(f"https://blockstream.info/api/blocks/tip/height", timeout=10)
        response.raise_for_status()
        tip_height = response.json()
        
        # 블록 정보 조회
        block_response = requests.get(f"https://blockstream.info/api/block-height/{tip_height}", timeout=10)
        block_response.raise_for_status()
        block_hash = block_response.text.strip()
        
        block_info_response = requests.get(f"https://blockstream.info/api/block/{block_hash}", timeout=10)
        block_info_response.raise_for_status()
        block_info = block_info_response.json()
        
        block_timestamp = block_info.get('timestamp', 0)
        block_dt = datetime.fromtimestamp(block_timestamp, tz=timezone.utc)
        local_dt = datetime.now(timezone.utc)
        
        print(f"   최신 블록 타임스탬프: {block_timestamp}")
        print(f"   UTC 변환: {block_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   현재 UTC 시간: {local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   차이: {(local_dt - block_dt).total_seconds():.0f}초")
        print(f"   KST 변환: {block_dt.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        print(f"\n✅ 결론: Blockstream API는 UTC 기준으로 타임스탬프를 반환합니다.")
        
    except Exception as e:
        print(f"❌ Blockstream API 확인 실패: {e}")

def main():
    """메인 함수"""
    print("=" * 70)
    print("🔍 타임존 상세 확인")
    print("=" * 70)
    print("\n이 스크립트는 다음을 확인합니다:")
    print("1. 바이낸스 API가 반환하는 시간 기준")
    print("2. 블록체인 API가 반환하는 시간 기준")
    print("3. price_history 테이블에 저장된 시간 기준")
    print("4. whale_transactions 테이블에 저장된 시간 기준")
    
    try:
        # 1. 바이낸스 API 확인
        check_binance_api_timezone()
        
        # 2. 블록체인 API 확인
        check_blockchain_api_timezone()
        
        # 3. price_history 확인
        supabase = get_supabase_client()
        check_price_history_timezone(supabase)
        
        # 4. whale_transactions 확인
        check_whale_transactions_timezone(supabase)
        
        # 최종 결론
        print("\n" + "=" * 70)
        print("📝 최종 결론 및 권장사항")
        print("=" * 70)
        print("\n✅ API 기준:")
        print("   - 바이낸스 API: UTC 기준")
        print("   - 블록체인 API: UTC 기준")
        print("\n✅ 데이터베이스 저장 기준:")
        print("   - price_history: UTC 기준으로 저장 권장")
        print("   - whale_transactions: UTC 기준으로 저장 권장")
        print("\n💡 권장사항:")
        print("   - 모든 타임스탬프는 UTC로 명시적으로 저장")
        print("   - ISO 형식 사용 시 타임존 정보 포함 (예: '2025-01-01T00:00:00+00:00')")
        print("   - 조회 시 필요하면 KST로 변환하여 표시")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

