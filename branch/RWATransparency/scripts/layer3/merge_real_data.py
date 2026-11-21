"""
Layer 3: 실제 데이터 기반 TDT 점수 계산 및 패널 데이터 통합

시뮬레이션이 아닌 실제 가격/공시 데이터를 결합합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os


def merge_panel_with_tdt(historical_path: str, disclosure_path: str, output_path: str):
    """
    실제 가격 시계열과 공시 기반 TDT 점수를 결합.
    
    핵심: TDT는 공시 데이터에서 도출되고, Y변수(변동성/유동성)는 
    시장 데이터에서 독립적으로 도출됨 → 순환 논리 제거
    """
    # 실제 가격 데이터 로드 (또는 처리된 패널 데이터)
    if not os.path.exists(historical_path):
        print(f"❌ Historical data not found: {historical_path}")
        print("Please run collect_historical_data.py first.")
        return None
    
    df_panel = pd.read_csv(historical_path)
    
    # 공시 데이터 로드
    if not os.path.exists(disclosure_path):
        print(f"❌ Disclosure data not found: {disclosure_path}")
        print("Please run collect_disclosure_data.py first.")
        return None
    
    df_disclosure = pd.read_csv(disclosure_path)
    
    print("=" * 60)
    print("Layer 3: Merging Real Data with TDT Scores")
    print("=" * 60)
    
    # TDT 점수 계산 (가중 합산)
    df_disclosure['tdt_score'] = (
        df_disclosure['latency_score'] / 3 +
        df_disclosure['completeness_score'] / 3 +
        df_disclosure['consistency_score'] / 3
    ).round(2)
    
    # 심볼 기준으로 병합
    # 공시 데이터의 symbol과 패널 데이터의 symbol 매칭
    tdt_cols = ['symbol', 'tdt_score', 'latency_score', 'completeness_score', 'consistency_score']
    
    # coin_id가 있으면 사용, 없으면 symbol 사용
    if 'coin_id' in df_panel.columns:
        merge_key = 'coin_id'
        df_disclosure_merge = df_disclosure.rename(columns={'coin_id': merge_key})
    else:
        merge_key = 'symbol'
        df_disclosure_merge = df_disclosure
    
    df_merged = df_panel.merge(
        df_disclosure_merge[tdt_cols + ([merge_key] if merge_key != 'symbol' else [])].drop_duplicates(),
        on=merge_key,
        how='left',
        suffixes=('', '_disclosure')
    )
    
    # 누락된 TDT 처리 (공시 정보 없으면 낮은 점수)
    df_merged['tdt_score'] = df_merged['tdt_score'].fillna(30)  # 정보 없으면 30점
    df_merged['latency_score'] = df_merged['latency_score'].fillna(30)
    df_merged['completeness_score'] = df_merged['completeness_score'].fillna(30)
    df_merged['consistency_score'] = df_merged['consistency_score'].fillna(30)
    
    # 거시 충격 변수 추가 (실제 시장 이벤트 기반)
    # 예: BTC 급락일, 금리 발표일 등
    df_merged['date'] = pd.to_datetime(df_merged['date'])
    
    # 간단한 거시 충격 정의: 전체 시장 평균 수익률이 -2% 이하인 날
    daily_avg_return = df_merged.groupby('date')['daily_return'].mean().reset_index()
    daily_avg_return.columns = ['date', 'market_avg_return']
    daily_avg_return['macro_shock'] = (daily_avg_return['market_avg_return'] < -0.02).astype(int)
    
    df_merged = df_merged.merge(daily_avg_return[['date', 'macro_shock']], on='date', how='left')
    df_merged['macro_shock'] = df_merged['macro_shock'].fillna(0).astype(int)
    
    # 저장
    df_merged.to_csv(output_path, index=False)
    
    print(f"✅ Merged panel data: {len(df_merged)} observations")
    print(f"   Tokens: {df_merged['symbol'].nunique()}")
    print(f"   Date range: {df_merged['date'].min()} ~ {df_merged['date'].max()}")
    print(f"   Shock days: {df_merged['macro_shock'].sum()}")
    print(f"\nSaved to: {output_path}")
    
    # TDT 분포 확인
    print("\n=== TDT Score Distribution ===")
    tdt_summary = df_merged.groupby('symbol')['tdt_score'].first().reset_index()
    print(tdt_summary.to_string(index=False))
    
    return df_merged


def main():
    base_path = os.path.dirname(__file__)
    
    # 실제 데이터 경로
    historical_path = os.path.join(base_path, '../../data/processed/real_panel_data.csv')
    disclosure_path = os.path.join(base_path, '../../data/raw/offchain_disclosure.csv')
    output_path = os.path.join(base_path, '../../data/processed/final_panel_data.csv')
    
    merge_panel_with_tdt(historical_path, disclosure_path, output_path)


if __name__ == "__main__":
    main()
