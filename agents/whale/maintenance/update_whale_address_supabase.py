#!/usr/bin/env python3
"""
whale_address_cleaned.csv 파일을 Supabase whale_address 테이블에 업데이트
기존 데이터는 유지하고 새로운 데이터는 추가, 같은 id가 있으면 업데이트
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def load_csv_data(csv_file: str) -> list:
    """CSV 파일을 읽어서 Supabase 형식으로 변환"""
    df = pd.read_csv(csv_file)
    
    records = []
    for _, row in df.iterrows():
        record = {
            'id': str(row['id']),
            'chain_type': str(row['chain_type']),
            'address': str(row['address']),
            'name_tag': str(row['name_tag']) if pd.notna(row['name_tag']) and row['name_tag'] != '' else None,
            'balance': str(row['balance']) if pd.notna(row['balance']) and row['balance'] != '' else None,
            'percentage': str(row['percentage']) if pd.notna(row['percentage']) and row['percentage'] != '' else None,
            'txn_count': str(row['txn_count']) if pd.notna(row['txn_count']) and row['txn_count'] != '' else None,
        }
        records.append(record)
    
    return records

def update_supabase(records: list) -> dict:
    """Supabase에 데이터 업로드 (upsert)"""
    # 환경 변수 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    # Supabase 클라이언트 생성
    supabase = create_client(supabase_url, supabase_key)
    
    print(f"\n📤 Supabase에 {len(records)}건 업로드 중...")
    
    # 기존 데이터 확인
    try:
        existing_response = supabase.table('whale_address').select('id,chain_type', count='exact').execute()
        existing_count = existing_response.count if hasattr(existing_response, 'count') else len(existing_response.data)
        print(f"   기존 데이터: {existing_count}건")
    except Exception as e:
        print(f"   ⚠️ 기존 데이터 확인 실패: {e}")
        existing_count = 0
    
    # 배치로 업로드 (한 번에 너무 많이 보내지 않도록)
    batch_size = 100
    total_uploaded = 0
    total_updated = 0
    total_inserted = 0
    errors = []
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # upsert 사용 (PRIMARY KEY가 (id, chain_type)이면 자동으로 처리)
            # PRIMARY KEY가 없으면 에러가 발생하므로, 개별 처리로 fallback
            # Supabase Python 클라이언트는 PRIMARY KEY를 자동 감지하므로 on_conflict 불필요
            response = supabase.table('whale_address').upsert(batch).execute()
            
            # 응답에서 실제 처리된 레코드 수 확인
            if response.data:
                # 기존 레코드인지 새 레코드인지 확인하기 위해 개별 체크
                for record in batch:
                    try:
                        # 기존 레코드 확인
                        check = supabase.table('whale_address').select('id').eq('id', record['id']).eq('chain_type', record['chain_type']).execute()
                        if check.data:
                            total_updated += 1
                        else:
                            total_inserted += 1
                    except:
                        total_inserted += 1
            
            total_uploaded += len(batch)
            if (i + batch_size) % 500 == 0 or i + batch_size >= len(records):
                print(f"   ✅ {total_uploaded}/{len(records)}건 처리 완료 (INSERT: {total_inserted}, UPDATE: {total_updated})")
        except Exception as e:
            error_msg = str(e)
            # PRIMARY KEY 관련 오류인 경우 개별 처리로 fallback
            if 'primary key' in error_msg.lower() or 'unique constraint' in error_msg.lower() or 'conflict' in error_msg.lower():
                print(f"   ⚠️ 배치 upsert 실패, 개별 처리로 전환: {error_msg[:100]}")
                # 개별 upsert 시도 (PRIMARY KEY가 없을 경우)
                for record in batch:
                    try:
                        # 먼저 기존 레코드 확인
                        existing = supabase.table('whale_address').select('*').eq('id', record['id']).eq('chain_type', record['chain_type']).execute()
                        if existing.data:
                            # 업데이트
                            supabase.table('whale_address').update(record).eq('id', record['id']).eq('chain_type', record['chain_type']).execute()
                            total_updated += 1
                        else:
                            # 삽입
                            supabase.table('whale_address').insert(record).execute()
                            total_inserted += 1
                        total_uploaded += 1
                    except Exception as e2:
                        errors.append(f"개별 처리 실패 ({record.get('id')}, {record.get('chain_type')}): {str(e2)[:100]}")
            else:
                print(f"   ❌ 배치 업로드 실패 (인덱스 {i}-{i+len(batch)-1}): {error_msg[:100]}")
                errors.append(f"배치 {i//batch_size + 1}: {error_msg[:100]}")
                # 개별 업로드 시도
                for record in batch:
                    try:
                        supabase.table('whale_address').upsert([record]).execute()
                        total_uploaded += 1
                    except Exception as e2:
                        errors.append(f"개별 업로드 실패 ({record.get('id')}, {record.get('chain_type')}): {str(e2)[:100]}")
    
    # 최종 데이터 확인
    try:
        final_response = supabase.table('whale_address').select('id,chain_type', count='exact').execute()
        final_count = final_response.count if hasattr(final_response, 'count') else len(final_response.data)
        print(f"\n   최종 데이터: {final_count}건")
    except Exception as e:
        print(f"   ⚠️ 최종 데이터 확인 실패: {e}")
        final_count = existing_count
    
    return {
        'total_records': len(records),
        'uploaded': total_uploaded,
        'inserted': total_inserted,
        'updated': total_updated,
        'existing_count': existing_count,
        'final_count': final_count,
        'errors': errors
    }

def main():
    """메인 함수"""
    print("=" * 70)
    print("📊 whale_address_cleaned.csv → Supabase 업데이트")
    print("=" * 70)
    
    csv_file = "whale_address_cleaned.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ 파일을 찾을 수 없습니다: {csv_file}")
        sys.exit(1)
    
    try:
        # CSV 데이터 로드
        print(f"\n📖 CSV 파일 읽기: {csv_file}")
        records = load_csv_data(csv_file)
        
        print(f"✅ 총 {len(records)}건의 레코드 준비 완료")
        
        # 체인별 통계
        df = pd.read_csv(csv_file)
        chain_stats = df['chain_type'].value_counts().sort_index()
        print("\n📊 체인별 통계:")
        for chain, count in chain_stats.items():
            print(f"   {chain}: {count}건")
        
        # Supabase 업데이트
        result = update_supabase(records)
        
        # 결과 출력
        print("\n" + "=" * 70)
        print("📊 업데이트 결과")
        print("=" * 70)
        print(f"처리할 레코드: {result['total_records']}건")
        print(f"업로드 완료: {result['uploaded']}건")
        print(f"  - 새로 추가: {result.get('inserted', 0)}건")
        print(f"  - 업데이트: {result.get('updated', 0)}건")
        print(f"기존 데이터: {result['existing_count']}건")
        print(f"최종 데이터: {result['final_count']}건")
        
        if result['errors']:
            print(f"\n⚠️ 오류 발생: {len(result['errors'])}건")
            for error in result['errors'][:10]:  # 처음 10개만 표시
                print(f"   - {error}")
            if len(result['errors']) > 10:
                print(f"   ... 외 {len(result['errors']) - 10}건")
        
        print("\n✅ 업데이트 완료!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

