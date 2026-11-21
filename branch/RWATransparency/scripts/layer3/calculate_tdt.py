"""
TDT (Transparency Digital Twin) Score Calculator

TDT는 RWA 토큰의 정보 품질을 0~100점으로 정량화합니다.
3가지 구성 요소:
1. Update Latency Score: 오프체인 공시 갱신 지연 정도
2. Completeness Score: 필수 정보 공개 비율
3. Consistency Score: 온체인-오프체인 데이터 정합성
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# === 가중치 설정 (버전별로 달라질 수 있음) ===
WEIGHTS = {
    'equal': {'latency': 1/3, 'completeness': 1/3, 'consistency': 1/3},
    'latency_focus': {'latency': 0.5, 'completeness': 0.25, 'consistency': 0.25},
    'consistency_focus': {'latency': 0.25, 'completeness': 0.25, 'consistency': 0.5}
}

# === 필수 공개 필드 정의 ===
REQUIRED_FIELDS = [
    'aum',                  # 운용자산규모
    'audit_report',         # 감사 보고서
    'custodian',            # 보관기관
    'collateral_type',      # 담보 유형
    'issuance_history',     # 발행 내역
    'redemption_policy',    # 상환 정책
    'management_fee',       # 운용 수수료
    'nav_frequency'         # NAV 공시 빈도
]


def calculate_latency_score(last_update_date: str, max_days: int = 30) -> float:
    """
    갱신 지연 점수 계산.
    - last_update_date: 마지막 공시 업데이트 날짜 (YYYY-MM-DD)
    - max_days: 허용 최대 지연일 (기본 30일, 이후 0점)
    
    Returns: 0~100 점수 (최근 업데이트일수록 높음)
    """
    if pd.isna(last_update_date) or last_update_date == '':
        return 0.0
    
    try:
        last_update = datetime.strptime(last_update_date, '%Y-%m-%d')
    except ValueError:
        return 0.0
    
    days_since_update = (datetime.now() - last_update).days
    
    if days_since_update <= 0:
        return 100.0
    elif days_since_update >= max_days:
        return 0.0
    else:
        # Linear decay: 100 -> 0 over max_days
        return max(0, 100 * (1 - days_since_update / max_days))


def calculate_completeness_score(available_fields: list) -> float:
    """
    정보 완전성 점수 계산.
    - available_fields: 해당 RWA가 공개하고 있는 필드 목록
    
    Returns: 0~100 점수 (공개 비율)
    """
    if not available_fields:
        return 0.0
    
    available_set = set(available_fields)
    required_set = set(REQUIRED_FIELDS)
    
    covered = len(available_set.intersection(required_set))
    total = len(required_set)
    
    return 100 * (covered / total)


def calculate_consistency_score(onchain_supply: float, offchain_aum: float, tolerance: float = 0.02) -> float:
    """
    온체인-오프체인 정합성 점수 계산.
    - onchain_supply: 온체인 총 공급량 (USD 환산)
    - offchain_aum: 오프체인 공시 AUM
    - tolerance: 허용 오차율 (기본 2%)
    
    Returns: 0~100 점수 (불일치율 낮을수록 높음)
    """
    if pd.isna(onchain_supply) or pd.isna(offchain_aum) or offchain_aum == 0:
        return 0.0
    
    # 불일치율 계산
    discrepancy = abs(onchain_supply - offchain_aum) / offchain_aum
    
    if discrepancy <= tolerance:
        return 100.0
    elif discrepancy >= 0.5:  # 50% 이상 차이면 0점
        return 0.0
    else:
        # Linear decay from 100 to 0 between tolerance and 0.5
        return max(0, 100 * (1 - (discrepancy - tolerance) / (0.5 - tolerance)))


def calculate_tdt_score(latency_score: float, completeness_score: float, consistency_score: float,
                        weight_version: str = 'equal') -> float:
    """
    최종 TDT 점수 계산 (가중 합산).
    """
    w = WEIGHTS.get(weight_version, WEIGHTS['equal'])
    
    tdt = (w['latency'] * latency_score +
           w['completeness'] * completeness_score +
           w['consistency'] * consistency_score)
    
    return round(tdt, 2)


def process_tdt_for_all_assets(market_data_path: str, offchain_data_path: str, output_path: str):
    """
    전체 RWA 자산에 대한 TDT 점수 일괄 계산.
    """
    # 시장 데이터 로드
    df_market = pd.read_csv(market_data_path)
    
    # 오프체인 데이터 로드 (있다면)
    if os.path.exists(offchain_data_path):
        df_offchain = pd.read_csv(offchain_data_path)
    else:
        # 오프체인 데이터 없으면 빈 DataFrame
        df_offchain = pd.DataFrame(columns=['asset', 'last_update', 'aum', 'available_fields'])
    
    results = []
    
    for _, row in df_market.iterrows():
        asset_id = row['id']
        onchain_mcap = row.get('market_cap', 0)
        
        # 오프체인 데이터 매칭
        offchain_row = df_offchain[df_offchain['asset'] == asset_id]
        
        if len(offchain_row) > 0:
            last_update = offchain_row.iloc[0].get('last_update', '')
            offchain_aum = offchain_row.iloc[0].get('aum', 0)
            available_fields = str(offchain_row.iloc[0].get('available_fields', '')).split(',')
        else:
            # 오프체인 데이터 없음 - 시연용 기본값
            last_update = (datetime.now() - timedelta(days=np.random.randint(1, 20))).strftime('%Y-%m-%d')
            offchain_aum = onchain_mcap * np.random.uniform(0.95, 1.05)  # 시연용: 5% 내외 변동
            available_fields = np.random.choice(REQUIRED_FIELDS, size=np.random.randint(4, 8), replace=False).tolist()
        
        # 점수 계산
        latency = calculate_latency_score(last_update)
        completeness = calculate_completeness_score(available_fields)
        consistency = calculate_consistency_score(onchain_mcap, offchain_aum)
        
        # TDT 계산 (3가지 버전)
        tdt_equal = calculate_tdt_score(latency, completeness, consistency, 'equal')
        tdt_latency = calculate_tdt_score(latency, completeness, consistency, 'latency_focus')
        tdt_consistency = calculate_tdt_score(latency, completeness, consistency, 'consistency_focus')
        
        results.append({
            'asset_id': asset_id,
            'symbol': row['symbol'],
            'name': row['name'],
            'market_cap': onchain_mcap,
            'last_update': last_update,
            'offchain_aum': offchain_aum,
            'latency_score': round(latency, 2),
            'completeness_score': round(completeness, 2),
            'consistency_score': round(consistency, 2),
            'tdt_equal': tdt_equal,
            'tdt_latency_focus': tdt_latency,
            'tdt_consistency_focus': tdt_consistency,
            'timestamp': datetime.now().isoformat()
        })
    
    df_result = pd.DataFrame(results)
    df_result.to_csv(output_path, index=False)
    print(f"TDT scores calculated for {len(df_result)} assets. Saved to {output_path}")
    return df_result


def main():
    base_path = os.path.dirname(__file__)
    market_data_path = os.path.join(base_path, '../../data/raw/market_data_latest.csv')
    offchain_data_path = os.path.join(base_path, '../../data/raw/offchain_enriched.csv')
    output_path = os.path.join(base_path, '../../data/processed/tdt_scores.csv')
    
    print("=== TDT Score Calculation Started ===")
    df_tdt = process_tdt_for_all_assets(market_data_path, offchain_data_path, output_path)
    print("\n=== TDT Score Summary ===")
    print(df_tdt[['symbol', 'latency_score', 'completeness_score', 'consistency_score', 'tdt_equal']].to_string(index=False))


if __name__ == "__main__":
    main()
