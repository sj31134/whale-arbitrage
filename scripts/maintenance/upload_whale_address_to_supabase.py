#!/usr/bin/env python3
"""
whale_address.xlsx 파일의 데이터를 Supabase whale_address 테이블에 업로드하는 스크립트
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict, Any

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 코인 이름 매핑 (Excel 탭 이름 -> chain_type)
COIN_MAPPING = {
    'BITCOIN': 'BTC',
    'ETHERIUM': 'ETH',  # ETHERIUM은 오타인 것 같지만 원본 그대로 사용
    'LITECOIN': 'LTC',
    'DOGECOIN': 'DOGE',
    'VERTCOIN': 'VTC',
}

def normalize_balance(balance_str: str) -> str:
    """Balance 문자열 정규화 (예: "248,598 BTC ($26,800,491,633)" -> "248,598 BTC")"""
    if pd.isna(balance_str) or balance_str == '':
        return ''
    # 괄호 안의 USD 가격 제거
    if '(' in str(balance_str):
        return str(balance_str).split('(')[0].strip()
    return str(balance_str).strip()

def normalize_percentage(percentage) -> str:
    """Percentage 정규화"""
    if pd.isna(percentage):
        return ''
    # 소수점을 퍼센트로 변환 (0.012500 -> "1.25%")
    if isinstance(percentage, (int, float)):
        return f"{percentage * 100:.4f}%"
    return str(percentage)

def process_excel_data(excel_file: str) -> List[Dict[str, Any]]:
    """Excel 파일을 읽어서 Supabase 형식으로 변환"""
    all_records = []
    
    # Excel 파일 로드
    wb = pd.ExcelFile(excel_file)
    
    for sheet_name in wb.sheet_names:
        chain_type = COIN_MAPPING.get(sheet_name.upper(), sheet_name.upper())
        print(f"\n📋 처리 중: {sheet_name} -> {chain_type}")
        
        # 탭 읽기
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # 빈 행 제거 (No가 NaN인 행)
        if 'No' in df.columns:
            df = df[df['No'].notna()].copy()
        
        print(f"   유효한 데이터: {len(df)}건")
        
        for idx, row in df.iterrows():
            # Address 필수 확인
            address = str(row.get('Address', '')).strip()
            if not address or address == 'nan' or address == '':
                continue
            
            # Name Tag 처리
            name_tag = None
            if 'Name Tag' in df.columns:
                name_tag_val = row.get('Name Tag')
                if pd.notna(name_tag_val) and str(name_tag_val).strip() != '':
                    name_tag = str(name_tag_val).strip()
            
            # Balance 처리
            balance = ''
            if 'Balance' in df.columns:
                balance = normalize_balance(row.get('Balance', ''))
            
            # Percentage 처리
            percentage = ''
            if 'Percentage' in df.columns:
                percentage = normalize_percentage(row.get('Percentage'))
            elif '% of coins' in df.columns:
                percentage = normalize_percentage(row.get('% of coins'))
            
            # Txn Count 처리
            txn_count = ''
            if 'Txn Count' in df.columns:
                txn_count_val = row.get('Txn Count')
                if pd.notna(txn_count_val):
                    txn_count = str(int(txn_count_val))
            elif 'Ins' in df.columns:
                # Ins + Outs를 합쳐서 거래 수로 사용
                ins = row.get('Ins', 0) if pd.notna(row.get('Ins')) else 0
                outs = row.get('Outs', 0) if pd.notna(row.get('Outs')) else 0
                total_txns = int(ins) + int(outs) if pd.notna(ins) and pd.notna(outs) else 0
                if total_txns > 0:
                    txn_count = str(total_txns)
            
            # ID 생성 (chain_type + 순번)
            no = row.get('No', idx + 1)
            if pd.isna(no):
                no = idx + 1
            record_id = f"{chain_type}{int(no):03d}"
            
            record = {
                'id': record_id,
                'chain_type': chain_type,
                'address': address,
                'name_tag': name_tag if name_tag else None,
                'balance': balance if balance else None,
                'percentage': percentage if percentage else None,
                'txn_count': txn_count if txn_count else None,
            }
            
            all_records.append(record)
    
    return all_records

def upload_to_supabase(records: List[Dict[str, Any]]) -> int:
    """Supabase에 데이터 업로드"""
    # 환경 변수 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    # Supabase 클라이언트 생성
    supabase = create_client(supabase_url, supabase_key)
    
    print(f"\n📤 Supabase에 {len(records)}건 업로드 중...")
    
    # 배치로 업로드 (한 번에 너무 많이 보내지 않도록)
    batch_size = 100
    total_uploaded = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # upsert 사용 (중복 시 업데이트)
            response = supabase.table('whale_address').upsert(batch).execute()
            total_uploaded += len(batch)
            print(f"   ✅ {total_uploaded}/{len(records)}건 업로드 완료")
        except Exception as e:
            print(f"   ❌ 배치 업로드 실패 (인덱스 {i}-{i+len(batch)-1}): {e}")
            # 개별 업로드 시도
            for record in batch:
                try:
                    supabase.table('whale_address').upsert([record]).execute()
                    total_uploaded += 1
                except Exception as e2:
                    print(f"      ⚠️ 개별 업로드 실패: {record.get('id')} - {e2}")
    
    return total_uploaded

def main():
    """메인 함수"""
    print("=" * 70)
    print("📊 whale_address.xlsx → Supabase 업로드")
    print("=" * 70)
    
    excel_file = "whale_address.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ 파일을 찾을 수 없습니다: {excel_file}")
        sys.exit(1)
    
    try:
        # Excel 데이터 처리
        print(f"\n📖 Excel 파일 읽기: {excel_file}")
        records = process_excel_data(excel_file)
        
        print(f"\n✅ 총 {len(records)}건의 레코드 준비 완료")
        
        # 체인별 통계
        chain_stats = {}
        for record in records:
            chain = record['chain_type']
            chain_stats[chain] = chain_stats.get(chain, 0) + 1
        
        print("\n📊 체인별 통계:")
        for chain, count in sorted(chain_stats.items()):
            print(f"   {chain}: {count}건")
        
        # Supabase 업로드
        print("\n" + "=" * 70)
        uploaded_count = upload_to_supabase(records)
        
        print("\n" + "=" * 70)
        print(f"✅ 업로드 완료: {uploaded_count}/{len(records)}건")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

