#!/usr/bin/env python3
"""
1. POLYGON, ARBITRUM, OPTIMISM, AVALANCHE, SOL, BASE 6개 네트워크의 USDC 데이터 삭제
2. usdc_ethereum_richlist_top100.csv를 읽어서 chain_type="USDC", name_tag="USDC"로 업로드
"""

import os
import sys
import pandas as pd
from pathlib import Path
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


def delete_usdc_networks(supabase):
    """
    6개 네트워크의 USDC 데이터 삭제
    POLYGON, ARBITRUM, OPTIMISM, AVALANCHE, SOL, BASE
    """
    print('=' * 80)
    print('🗑️  USDC 네트워크 데이터 삭제')
    print('=' * 80)
    
    networks_to_delete = ['POLYGON', 'ARBITRUM', 'OPTIMISM', 'AVALANCHE', 'SOL', 'BASE']
    
    total_deleted = 0
    
    for chain_type in networks_to_delete:
        try:
            # 삭제 전 개수 확인
            response_before = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain_type).eq('name_tag', 'USD Coin').execute()
            count_before = response_before.count if hasattr(response_before, 'count') else len(response_before.data)
            
            if count_before > 0:
                # 삭제 실행
                delete_response = supabase.table('whale_address').delete().eq('chain_type', chain_type).eq('name_tag', 'USD Coin').execute()
                deleted_count = len(delete_response.data) if delete_response.data else count_before
                total_deleted += deleted_count
                print(f'  ✅ {chain_type}: {deleted_count}건 삭제 완료')
            else:
                print(f'  ⚠️  {chain_type}: 삭제할 데이터 없음 (0건)')
                
        except Exception as e:
            print(f'  ❌ {chain_type} 삭제 실패: {e}')
    
    print(f'\n  📊 총 삭제된 레코드: {total_deleted}건')
    return total_deleted


def upload_usdc_ethereum(supabase, csv_path: Path):
    """
    usdc_ethereum_richlist_top100.csv를 읽어서 
    chain_type="USDC", name_tag="USDC"로 업로드
    """
    print('\n' + '=' * 80)
    print('📤 USDC Ethereum 데이터 업로드')
    print('=' * 80)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"❌ CSV 파일을 찾을 수 없습니다: {csv_path}")
    
    # CSV 파일 읽기
    df = pd.read_csv(csv_path)
    print(f'  📄 CSV 파일 읽기 완료: {len(df)}건')
    
    # 레코드 변환
    records = []
    for _, row in df.iterrows():
        try:
            rank = int(row.get('rank', 0))
            address = str(row.get('address', '')).strip()
            
            # 필수 필드 확인
            if not address:
                continue
            
            # ID 생성: USDC{rank:03d}
            id_val = f"USDC{rank:03d}"
            
            # 주소 정규화 (EVM 주소는 소문자로)
            if address.startswith('0x'):
                address = address.lower()
            
            # whale_address 스키마에 맞게 변환
            record = {
                'id': id_val,
                'chain_type': 'USDC',  # chain_type을 "USDC"로 설정
                'address': address,
                'name_tag': 'USDC',  # name_tag를 "USDC"로 설정
                'balance': None,
                'percentage': None,
                'txn_count': None
            }
            
            records.append(record)
            
        except Exception as e:
            print(f'    ⚠️ 행 처리 오류 (rank={row.get("rank", "?")}): {e}')
            continue
    
    print(f'  ✅ 변환된 레코드: {len(records)}건')
    
    if not records:
        print('  ❌ 업로드할 레코드가 없습니다.')
        return 0
    
    # Supabase에 업로드 (배치 처리)
    print(f'\n  💾 Supabase에 업로드 중...')
    batch_size = 100
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
            
            print(f'    ✅ 배치 {i//batch_size + 1}: {uploaded_count}건 업로드 완료')
            
        except Exception as e:
            print(f'    ❌ 배치 {i//batch_size + 1} 업로드 실패: {e}')
            # 개별 레코드로 재시도
            for record in batch:
                try:
                    supabase.table('whale_address').upsert(
                        [record],
                        on_conflict='id,chain_type'
                    ).execute()
                    total_uploaded += 1
                except Exception as e2:
                    print(f'      ⚠️ 개별 레코드 업로드 실패 ({record.get("id")}): {e2}')
    
    print(f'\n  📊 총 업로드된 레코드: {total_uploaded}건')
    return total_uploaded


def verify_upload(supabase):
    """업로드 결과 확인"""
    print('\n' + '=' * 80)
    print('✅ 업로드 결과 확인')
    print('=' * 80)
    
    # USDC chain_type 데이터 확인
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', 'USDC').eq('name_tag', 'USDC').execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'  USDC (chain_type="USDC", name_tag="USDC"): {count}건')
    
    # 샘플 데이터 출력
    if count > 0:
        sample_response = supabase.table('whale_address').select('*').eq('chain_type', 'USDC').eq('name_tag', 'USDC').limit(3).execute()
        print('\n  📋 샘플 데이터 (상위 3건):')
        for i, record in enumerate(sample_response.data, 1):
            print(f'    [{i}] ID={record.get("id")}, Address={record.get("address")[:20]}...')
    
    # 삭제된 네트워크 확인 (0건이어야 함)
    deleted_networks = ['POLYGON', 'ARBITRUM', 'OPTIMISM', 'AVALANCHE', 'SOL', 'BASE']
    print('\n  🗑️  삭제된 네트워크 확인 (name_tag="USD Coin"):')
    for chain_type in deleted_networks:
        response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain_type).eq('name_tag', 'USD Coin').execute()
        count = response.count if hasattr(response, 'count') else len(response.data)
        status = '✅' if count == 0 else '⚠️'
        print(f'    {status} {chain_type}: {count}건')


def main():
    """메인 함수"""
    print('=' * 80)
    print('🐋 USDC 데이터 정리 및 Ethereum 데이터 업로드')
    print('=' * 80)
    
    try:
        # Supabase 클라이언트 생성
        supabase = get_supabase_client()
        
        # 1단계: 6개 네트워크의 USDC 데이터 삭제
        deleted_count = delete_usdc_networks(supabase)
        
        # 2단계: Ethereum USDC 데이터 업로드
        csv_path = PROJECT_ROOT / 'usdc_ethereum_richlist_top100.csv'
        uploaded_count = upload_usdc_ethereum(supabase, csv_path)
        
        # 3단계: 결과 확인
        verify_upload(supabase)
        
        # 최종 요약
        print('\n' + '=' * 80)
        print('✅ 작업 완료')
        print('=' * 80)
        print(f'  📊 삭제된 레코드: {deleted_count}건')
        print(f'  📊 업로드된 레코드: {uploaded_count}건')
        
    except KeyboardInterrupt:
        print('\n\n⚠️  사용자에 의해 중단되었습니다.')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

