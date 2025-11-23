#!/usr/bin/env python3
"""
BNB, USDC, XRP 고래 지갑 주소를 whale_address 테이블에 업로드
CSV 파일을 읽어서 whale_address 스키마에 맞게 변환 후 Supabase에 업로드
"""

import os
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Set
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def get_existing_ids(supabase) -> Set[tuple]:
    """
    기존 whale_address 테이블의 (id, chain_type) 조합 조회
    
    Returns:
    --------
    Set[tuple] : (id, chain_type) 튜플 Set
    """
    try:
        response = supabase.table('whale_address').select('id, chain_type').execute()
        existing = set()
        for row in response.data:
            id_val = row.get('id', '').strip()
            chain_type = row.get('chain_type', '').strip()
            if id_val and chain_type:
                existing.add((id_val, chain_type))
        return existing
    except Exception as e:
        print(f"⚠️ 기존 ID 조회 실패: {e}")
        return set()


def get_coin_full_name(coin_symbol: str) -> str:
    """코인 심볼을 전체 이름으로 변환"""
    coin_names = {
        'BNB': 'Binance Coin',
        'USDC': 'USD Coin',
        'XRP': 'Ripple'
    }
    return coin_names.get(coin_symbol.upper(), coin_symbol)


def process_csv_file(csv_path: Path, existing_ids: Set[tuple]) -> List[Dict]:
    """
    CSV 파일을 읽어서 whale_address 스키마에 맞게 변환
    
    Parameters:
    -----------
    csv_path : Path
        CSV 파일 경로
    existing_ids : Set[tuple]
        기존 (id, chain_type) 조합 Set
    
    Returns:
    --------
    List[Dict] : 변환된 레코드 리스트
    """
    try:
        df = pd.read_csv(csv_path)
        print(f"\n  📄 {csv_path.name} 읽기 완료: {len(df)}건")
        
        records = []
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                rank = int(row.get('rank', 0))
                address = str(row.get('address', '')).strip()
                chain_type = str(row.get('chain_type', '')).strip().upper()
                coin_symbol = str(row.get('coin_symbol', '')).strip().upper()
                network = str(row.get('network', '')).strip().lower() if 'network' in row else ''
                
                # 필수 필드 확인
                if not address or not chain_type or not coin_symbol:
                    skipped_count += 1
                    continue
                
                # ID 생성: {chain_type}{rank:03d}
                id_val = f"{chain_type}{rank:03d}"
                
                # 중복 확인
                if (id_val, chain_type) in existing_ids:
                    # 이미 존재하는 경우 건너뛰기 (또는 다른 ID 생성)
                    # 여기서는 건너뛰기로 처리
                    skipped_count += 1
                    continue
                
                # name_tag 생성
                name_tag = get_coin_full_name(coin_symbol)
                
                # whale_address 스키마에 맞게 변환
                record = {
                    'id': id_val,
                    'chain_type': chain_type,
                    'address': address.lower() if address.startswith('0x') else address,  # EVM 주소는 소문자로
                    'name_tag': name_tag,
                    'balance': None,
                    'percentage': None,
                    'txn_count': None
                }
                
                records.append(record)
                existing_ids.add((id_val, chain_type))  # 중복 방지를 위해 추가
                
            except Exception as e:
                print(f"    ⚠️ 행 처리 오류: {e}")
                skipped_count += 1
                continue
        
        if skipped_count > 0:
            print(f"    ⚠️ 건너뛴 레코드: {skipped_count}건")
        
        return records
        
    except Exception as e:
        print(f"  ❌ CSV 파일 읽기 실패 ({csv_path.name}): {e}")
        return []


def upload_to_supabase(supabase, records: List[Dict], batch_size: int = 100) -> int:
    """
    변환된 레코드를 Supabase에 업로드
    
    Parameters:
    -----------
    supabase : Client
        Supabase 클라이언트
    records : List[Dict]
        업로드할 레코드 리스트
    batch_size : int
        배치 크기
    
    Returns:
    --------
    int : 업로드된 레코드 수
    """
    if not records:
        return 0
    
    print(f"\n  💾 Supabase에 업로드 중... (총 {len(records)}건)")
    
    total_uploaded = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        try:
            # upsert로 기존 데이터 업데이트 및 새 데이터 추가
            response = supabase.table('whale_address').upsert(
                batch,
                on_conflict='id,chain_type'  # 복합 키 기반 upsert
            ).execute()
            
            uploaded_count = len(response.data) if response.data else len(batch)
            total_uploaded += uploaded_count
            
            print(f"    ✅ 배치 {i//batch_size + 1}: {uploaded_count}건 업로드 완료")
            
        except Exception as e:
            print(f"    ❌ 배치 {i//batch_size + 1} 업로드 실패: {e}")
            # 개별 레코드로 재시도
            for record in batch:
                try:
                    supabase.table('whale_address').upsert(
                        [record],
                        on_conflict='id,chain_type'
                    ).execute()
                    total_uploaded += 1
                except Exception as e2:
                    print(f"      ⚠️ 개별 레코드 업로드 실패 ({record.get('id')}): {e2}")
    
    return total_uploaded


def main():
    """메인 함수"""
    print("=" * 70)
    print("🐋 BNB, USDC, XRP 고래 지갑 주소를 whale_address 테이블에 업로드")
    print("=" * 70)
    
    try:
        # Supabase 클라이언트 생성
        supabase = get_supabase_client()
        
        # 기존 ID 조회 (중복 방지)
        print("\n[1단계] 기존 whale_address 데이터 확인 중...")
        existing_ids = get_existing_ids(supabase)
        print(f"  ✅ 기존 레코드: {len(existing_ids)}건")
        
        # CSV 파일 목록
        csv_files = [
            # BNB
            PROJECT_ROOT / 'bnb_mainnet_richlist_top100.csv',
            # USDC (8개 네트워크)
            PROJECT_ROOT / 'usdc_ethereum_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_bsc_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_polygon_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_arbitrum_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_optimism_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_avalanche_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_solana_richlist_top100.csv',
            PROJECT_ROOT / 'usdc_base_richlist_top100.csv',
            # XRP
            PROJECT_ROOT / 'xrp_mainnet_richlist_top100.csv',
        ]
        
        # 존재하는 CSV 파일만 필터링
        existing_csv_files = [f for f in csv_files if f.exists()]
        print(f"\n[2단계] CSV 파일 확인: {len(existing_csv_files)}개 파일 발견")
        
        if not existing_csv_files:
            print("❌ 처리할 CSV 파일이 없습니다.")
            return
        
        # 모든 CSV 파일 처리
        print("\n[3단계] CSV 파일 처리 중...")
        all_records = []
        
        for csv_file in existing_csv_files:
            records = process_csv_file(csv_file, existing_ids)
            all_records.extend(records)
        
        print(f"\n  ✅ 총 {len(all_records)}건의 레코드 변환 완료")
        
        if not all_records:
            print("❌ 업로드할 레코드가 없습니다.")
            return
        
        # Supabase에 업로드
        print("\n[4단계] Supabase에 업로드 중...")
        uploaded_count = upload_to_supabase(supabase, all_records)
        
        # 결과 출력
        print("\n" + "=" * 70)
        print("✅ 업로드 완료")
        print("=" * 70)
        print(f"📊 업로드 통계:")
        print(f"   - 변환된 레코드: {len(all_records)}건")
        print(f"   - 업로드된 레코드: {uploaded_count}건")
        
        # 체인별 통계 확인
        print("\n[5단계] 업로드 후 체인별 통계 확인...")
        chain_types_to_check = ['BSC', 'ETH', 'POLYGON', 'ARBITRUM', 'OPTIMISM', 'AVALANCHE', 'SOL', 'BASE', 'XRP']
        
        for chain_type in chain_types_to_check:
            response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain_type).limit(1).execute()
            count = response.count if hasattr(response, 'count') else len(response.data)
            if count > 0:
                print(f"   - {chain_type}: {count}건")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

