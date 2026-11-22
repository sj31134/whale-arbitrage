#!/usr/bin/env python3
"""
whale_address.xlsx 파일을 정제하여 Supabase whale_address 테이블 형식의 CSV로 변환
"""

import pandas as pd
import re
from pathlib import Path

# 코인 이름 매핑 (Excel 탭 이름 -> chain_type)
COIN_MAPPING = {
    'BITCOIN': 'BTC',
    'ETHERIUM': 'ETH',
    'LITECOIN': 'LTC',
    'DOGECOIN': 'DOGE',
    'VERTCOIN': 'VTC',
}

def extract_address(address_str: str) -> str:
    """
    지갑 주소 추출
    "지갑주소 wallet:binance" 형식에서 지갑주소만 추출
    "wallet:"로만 시작하는 경우는 주소가 없으므로 빈 문자열 반환
    """
    if pd.isna(address_str) or address_str == '':
        return ''
    
    address_str = str(address_str).strip()
    
    # "wallet:"로 시작하는 경우는 주소가 없음 (제외)
    if address_str.lower().startswith('wallet:'):
        return ''
    
    # "wallet:" 패턴이 있으면 그 앞부분만 추출
    if 'wallet:' in address_str.lower():
        # "wallet:" 앞의 주소 부분만 추출
        parts = address_str.split('wallet:')
        if len(parts) > 0 and parts[0].strip():
            return parts[0].strip()
        # wallet:만 있고 주소가 없으면 빈 문자열
        return ''
    
    # 일반적인 주소 형식 (공백으로 구분된 첫 번째 부분)
    parts = address_str.split()
    if len(parts) > 0:
        # 주소로 보이는 부분만 반환
        first_part = parts[0].strip()
        # 주소 형식 확인 (최소 길이 체크)
        if len(first_part) >= 10:  # 최소 주소 길이
            return first_part
    
    return address_str

def extract_name_tag(address_str: str) -> str:
    """
    Name Tag 추출 (wallet:binance 같은 부분)
    """
    if pd.isna(address_str) or address_str == '':
        return None
    
    address_str = str(address_str).strip()
    
    # "wallet:" 패턴이 있으면 그 부분을 name_tag로
    if 'wallet:' in address_str.lower():
        # "wallet:" 뒤의 부분 추출
        match = re.search(r'wallet:\s*([^\s]+)', address_str, re.IGNORECASE)
        if match:
            return f"wallet:{match.group(1)}"
        # 또는 전체 "wallet:" 부분
        parts = address_str.split('wallet:')
        if len(parts) > 1:
            tag = parts[1].strip()
            return f"wallet:{tag}" if not tag.startswith('wallet:') else tag
    
    return None

def normalize_balance(balance_str) -> str:
    """Balance 문자열 정규화"""
    if pd.isna(balance_str) or balance_str == '':
        return ''
    
    balance_str = str(balance_str).strip()
    
    # 괄호 안의 USD 가격 제거
    if '(' in balance_str:
        balance_str = balance_str.split('(')[0].strip()
    
    return balance_str

def normalize_percentage(percentage) -> str:
    """Percentage 정규화 (소수점을 퍼센트로)"""
    if pd.isna(percentage):
        return ''
    
    if isinstance(percentage, (int, float)):
        return f"{percentage * 100:.4f}%"
    
    # 이미 퍼센트 형식인 경우
    percentage_str = str(percentage).strip()
    if '%' in percentage_str:
        return percentage_str
    
    # 숫자만 있는 경우 퍼센트로 변환
    try:
        num = float(percentage_str)
        return f"{num * 100:.4f}%"
    except:
        return percentage_str

def get_txn_count(row, df_columns) -> str:
    """거래 수 추출"""
    # Txn Count 컬럼이 있으면 사용
    if 'Txn Count' in df_columns:
        txn_count = row.get('Txn Count')
        if pd.notna(txn_count):
            return str(int(txn_count))
    
    # Ins + Outs 합산
    if 'Ins' in df_columns and 'Outs' in df_columns:
        ins = row.get('Ins', 0)
        outs = row.get('Outs', 0)
        
        ins_val = int(ins) if pd.notna(ins) else 0
        outs_val = int(outs) if pd.notna(outs) else 0
        
        total = ins_val + outs_val
        if total > 0:
            return str(total)
    
    return ''

def process_excel_to_csv(excel_file: str, output_csv: str):
    """Excel 파일을 정제하여 CSV로 변환"""
    all_records = []
    
    # Excel 파일 로드
    wb = pd.ExcelFile(excel_file)
    
    print("=" * 70)
    print("📊 whale_address.xlsx 파일 정제 중...")
    print("=" * 70)
    
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
            # Address 필수 확인 및 정제
            address_raw = row.get('Address', '')
            if pd.isna(address_raw) or str(address_raw).strip() == '':
                continue
            
            # 지갑 주소 추출
            address = extract_address(str(address_raw))
            # 주소가 없거나 너무 짧으면 제외 (wallet:만 있는 경우)
            if not address or address == '' or len(address) < 10:
                continue
            
            # Name Tag 추출
            name_tag = None
            # ETHERIUM 탭에는 별도의 Name Tag 컬럼이 있음
            if 'Name Tag' in df.columns:
                name_tag_val = row.get('Name Tag')
                if pd.notna(name_tag_val) and str(name_tag_val).strip() != '':
                    name_tag = str(name_tag_val).strip()
            else:
                # 다른 탭에서는 address에서 추출
                name_tag = extract_name_tag(str(address_raw))
            
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
            txn_count = get_txn_count(row, df.columns)
            
            # ID 생성 (chain_type + 순번)
            no = row.get('No', idx + 1)
            if pd.isna(no):
                no = idx + 1
            try:
                record_id = f"{chain_type}{int(no):03d}"
            except:
                record_id = f"{chain_type}{idx + 1:03d}"
            
            record = {
                'id': record_id,
                'chain_type': chain_type,
                'address': address,
                'name_tag': name_tag if name_tag else '',
                'balance': balance if balance else '',
                'percentage': percentage if percentage else '',
                'txn_count': txn_count if txn_count else '',
            }
            
            all_records.append(record)
    
    # DataFrame 생성
    df_output = pd.DataFrame(all_records)
    
    # CSV로 저장
    df_output.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 70)
    print(f"✅ CSV 파일 생성 완료: {output_csv}")
    print(f"   총 {len(all_records)}건의 레코드")
    print("=" * 70)
    
    # 체인별 통계
    chain_stats = df_output['chain_type'].value_counts().sort_index()
    print("\n📊 체인별 통계:")
    for chain, count in chain_stats.items():
        print(f"   {chain}: {count}건")
    
    # 샘플 데이터 출력
    print("\n📋 샘플 데이터 (상위 5건):")
    print(df_output.head(5).to_string(index=False))
    
    return df_output

def main():
    """메인 함수"""
    excel_file = "whale_address.xlsx"
    output_csv = "whale_address_cleaned.csv"
    
    if not Path(excel_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {excel_file}")
        return
    
    try:
        df = process_excel_to_csv(excel_file, output_csv)
        print(f"\n✅ 정제 완료! CSV 파일: {output_csv}")
        print(f"   이제 이 CSV 파일을 Supabase에 업로드할 수 있습니다.")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

