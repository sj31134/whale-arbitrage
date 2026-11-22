#!/usr/bin/env python3
"""
whale_address_cleaned.csv 파일의 name_tag 빈 값을 chain_type의 full name으로 채우기
"""

import pandas as pd

# Chain type -> Full name 매핑
CHAIN_FULL_NAMES = {
    'BTC': 'Bitcoin',
    'ETH': 'Ethereum',
    'LTC': 'Litecoin',
    'DOGE': 'Dogecoin',
    'VTC': 'Vertcoin',
}

def main():
    csv_file = "whale_address_cleaned.csv"
    output_csv = "whale_address_cleaned.csv"  # 같은 파일에 덮어쓰기
    
    print("=" * 70)
    print("📝 name_tag 빈 값 채우기")
    print("=" * 70)
    
    # CSV 파일 읽기
    df = pd.read_csv(csv_file)
    
    print(f"\n✅ CSV 파일 로드 완료: {len(df)}건")
    
    # name_tag가 빈 값인 행 확인
    empty_name_tag = (df['name_tag'].isna()) | (df['name_tag'] == '')
    empty_count = empty_name_tag.sum()
    
    print(f"\n📊 name_tag 빈 값: {empty_count}건")
    
    # chain_type별 빈 값 통계
    print("\n체인별 name_tag 빈 값 통계:")
    for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
        chain_empty = ((df['chain_type'] == chain) & empty_name_tag).sum()
        print(f"  {chain}: {chain_empty}건")
    
    # name_tag가 빈 값인 경우 chain_type의 full name으로 채우기
    for chain_code, full_name in CHAIN_FULL_NAMES.items():
        mask = (df['chain_type'] == chain_code) & empty_name_tag
        df.loc[mask, 'name_tag'] = full_name
    
    # 결과 확인
    filled_count = ((df['name_tag'].isna()) | (df['name_tag'] == '')).sum()
    print(f"\n✅ name_tag 채우기 완료")
    print(f"   남은 빈 값: {filled_count}건")
    
    # CSV 파일 저장
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ CSV 파일 저장 완료: {output_csv}")
    
    # 샘플 데이터 확인
    print("\n📋 샘플 데이터 (name_tag가 채워진 행):")
    for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
        sample = df[df['chain_type'] == chain].iloc[0]
        print(f"\n{chain}:")
        print(f"  ID: {sample['id']}")
        print(f"  Address: {sample['address'][:50]}..." if len(sample['address']) > 50 else f"  Address: {sample['address']}")
        print(f"  Name Tag: {sample['name_tag']}")
        print(f"  Balance: {sample['balance']}")

if __name__ == '__main__':
    main()



