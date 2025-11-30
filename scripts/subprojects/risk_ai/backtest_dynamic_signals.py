#!/usr/bin/env python3
"""
동적 변수 기반 시그널 백테스트

각 동적 변수에 대해 임계값 기반 시그널을 생성하고,
백테스트를 실행하여 수익률, Sharpe Ratio, Maximum Drawdown을 계산합니다.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

DB_PATH = ROOT / "data" / "project.db"
OUTPUT_DIR = ROOT / "data" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_price_data(coin: str = "BTC", start_date: str = "2022-01-01") -> pd.DataFrame:
    """가격 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    symbol = f"{coin}USDT"
    
    query = f"""
    SELECT 
        date,
        close as price
    FROM binance_spot_daily
    WHERE symbol = '{symbol}'
    AND date >= '{start_date}'
    ORDER BY date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if len(df) == 0:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    return df


def generate_signals(
    dynamic_df: pd.DataFrame,
    variable: str,
    threshold: float,
    direction: str = "above"  # "above" or "below"
) -> pd.Series:
    """시그널 생성"""
    if variable not in dynamic_df.columns:
        return pd.Series(0, index=dynamic_df.index)
    
    values = dynamic_df[variable].fillna(0)
    
    if direction == "above":
        signals = (values > threshold).astype(int)
    else:  # below
        signals = (values < threshold).astype(int)
    
    return signals


def calculate_returns(price_df: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
    """수익률 계산"""
    df = price_df.copy()
    df['signal'] = signals.values[:len(df)]
    df['price_change'] = df['price'].pct_change()
    
    # 시그널이 1일 때 매수, 다음날 매도
    df['return'] = df['signal'].shift(1) * df['price_change']
    df['cumulative_return'] = (1 + df['return']).cumprod() - 1
    
    return df


def calculate_metrics(returns: pd.Series) -> Dict:
    """성능 지표 계산"""
    if len(returns) == 0 or returns.sum() == 0:
        return {
            'total_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'total_trades': 0
        }
    
    # 총 수익률
    total_return = (1 + returns).prod() - 1
    
    # Sharpe Ratio (연율화, 무위험 수익률 0 가정)
    if returns.std() > 0:
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # 연율화
    else:
        sharpe_ratio = 0
    
    # Maximum Drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = abs(drawdown.min())
    
    # 승률
    positive_returns = returns[returns != 0]
    if len(positive_returns) > 0:
        win_rate = (positive_returns > 0).sum() / len(positive_returns)
    else:
        win_rate = 0
    
    # 총 거래 횟수
    total_trades = (returns != 0).sum()
    
    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'total_trades': total_trades
    }


def backtest_single_variable(
    dynamic_df: pd.DataFrame,
    price_df: pd.DataFrame,
    variable: str,
    thresholds: List[float] = [-0.1, -0.05, 0, 0.05, 0.1]
) -> pd.DataFrame:
    """단일 변수에 대한 백테스트"""
    results = []
    
    for threshold in thresholds:
        # 양수 임계값 (상승 시그널)
        signals_above = generate_signals(dynamic_df, variable, threshold, "above")
        returns_above = calculate_returns(price_df, signals_above)
        metrics_above = calculate_metrics(returns_above['return'].fillna(0))
        
        results.append({
            'variable': variable,
            'threshold': threshold,
            'direction': 'above',
            **metrics_above
        })
        
        # 음수 임계값 (하락 시그널)
        signals_below = generate_signals(dynamic_df, variable, -threshold, "below")
        returns_below = calculate_returns(price_df, signals_below)
        metrics_below = calculate_metrics(returns_below['return'].fillna(0))
        
        results.append({
            'variable': variable,
            'threshold': -threshold,
            'direction': 'below',
            **metrics_below
        })
    
    return pd.DataFrame(results)


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="동적 변수 백테스트")
    parser.add_argument("--coin", type=str, default="BTC", choices=["BTC", "ETH"])
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    parser.add_argument("--variables", type=str, nargs="+", default=None,
                       help="분석할 변수 목록 (지정하지 않으면 모든 동적 변수)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("📊 동적 변수 백테스트")
    print("=" * 80)
    print(f"코인: {args.coin}")
    print(f"시작일: {args.start_date}")
    print()
    
    # 1. 가격 데이터 로드
    print("[1/4] 가격 데이터 로드 중...")
    price_df = load_price_data(args.coin, args.start_date)
    
    if price_df.empty:
        print("❌ 가격 데이터를 불러올 수 없습니다.")
        return
    
    print(f"   ✅ {len(price_df)}건 로드 ({price_df['date'].min()} ~ {price_df['date'].max()})")
    
    # 2. 동적 변수 포함 피처 생성
    print("\n[2/4] 동적 변수 포함 피처 생성 중...")
    fe = FeatureEngineer()
    raw_df = fe.load_raw_data(args.start_date, coin=args.coin)
    
    if raw_df.empty:
        print("❌ 원본 데이터를 불러올 수 없습니다.")
        return
    
    dynamic_df, features = fe.create_features(raw_df, include_dynamic=True)
    print(f"   ✅ {len(features)}개 피처 생성")
    
    # 동적 변수 필터링
    dynamic_features = [f for f in features if any(x in f for x in ['delta', 'accel', 'slope', 'momentum', 'stability'])]
    
    if args.variables:
        dynamic_features = [f for f in dynamic_features if f in args.variables]
    
    print(f"   ✅ {len(dynamic_features)}개 동적 변수 분석 대상")
    
    # 3. 날짜 기준 병합
    print("\n[3/4] 데이터 병합 중...")
    merged = pd.merge(
        dynamic_df[['date'] + dynamic_features],
        price_df[['date', 'price']],
        on='date',
        how='inner'
    )
    
    if len(merged) == 0:
        print("❌ 데이터 병합 실패")
        return
    
    print(f"   ✅ {len(merged)}건 병합 완료")
    
    # 4. 백테스트 실행
    print("\n[4/4] 백테스트 실행 중...")
    all_results = []
    
    for i, var in enumerate(dynamic_features):
        print(f"   [{i+1}/{len(dynamic_features)}] {var} 분석 중...")
        try:
            var_results = backtest_single_variable(merged, merged, var)
            all_results.append(var_results)
        except Exception as e:
            print(f"      ⚠️ 오류: {e}")
            continue
    
    if not all_results:
        print("❌ 백테스트 결과가 없습니다.")
        return
    
    results_df = pd.concat(all_results, ignore_index=True)
    
    # 5. 결과 저장
    output_file = OUTPUT_DIR / f"dynamic_backtest_{args.coin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ 결과 저장: {output_file}")
    
    # 6. 상위 결과 출력
    print("\n" + "=" * 80)
    print("📊 상위 10개 최고 수익률 시그널")
    print("=" * 80)
    
    top10 = results_df.nlargest(10, 'total_return', keep='all')
    if len(top10) > 0:
        print(top10[['variable', 'threshold', 'direction', 'total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'total_trades']].to_string())
    else:
        print("결과가 없습니다.")
    
    print("\n" + "=" * 80)
    print("✅ 백테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

