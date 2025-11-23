#!/usr/bin/env python3
"""
개선된 전략 테스트 및 비교
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))

from backtest_engine_optimized import OptimizedArbitrageBacktest

def test_strategy(name, **kwargs):
    """전략 테스트"""
    print(f"\n{'='*60}")
    print(f"전략 테스트: {name}")
    print(f"{'='*60}")
    
    backtest = OptimizedArbitrageBacktest(**kwargs)
    
    START_DATE = "2024-01-01"
    END_DATE = "2025-11-22"
    
    df = backtest.load_data(START_DATE, END_DATE)
    df = backtest.calculate_indicators(df)
    benchmark_return = backtest.calculate_benchmark(df)
    df = backtest.generate_signals(df)
    trades_df, daily_capital_df = backtest.run_backtest(df)
    metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
    
    print(f"거래 횟수: {metrics['total_trades']}회")
    print(f"최종 수익률: {metrics['final_return'] * 100:.2f}%")
    print(f"연율화 수익률: {metrics['annualized_return'] * 100:.2f}%")
    print(f"승률: {metrics['win_rate'] * 100:.1f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"MDD: {metrics['mdd'] * 100:.2f}%")
    print(f"벤치마크: {metrics['benchmark_return'] * 100:.2f}%")
    print(f"초과 수익률: {metrics['excess_return'] * 100:.2f}%")
    
    if not trades_df.empty:
        print(f"\n거래소 쌍별 통계:")
        pair_stats = trades_df.groupby('pair').agg({
            'return': ['count', 'mean', lambda x: (x > 0).mean()],
            'profit': 'sum'
        })
        print(pair_stats)
    
    return metrics

def main():
    print("🧪 개선된 전략 테스트 시작")
    
    strategies = [
        ("기존 전략 (참고)", {
            "entry_z": 2.0,
            "exit_z": 0.5,
            "exclude_upbit_binance": False
        }),
        ("전략 1: upbit_binance 제외", {
            "entry_z": 2.0,
            "exit_z": 0.5,
            "exclude_upbit_binance": True
        }),
        ("전략 2: 진입 조건 강화 (2.5)", {
            "entry_z": 2.5,
            "exit_z": 0.5,
            "exclude_upbit_binance": False
        }),
        ("전략 3: 진입 강화 + upbit_binance 제외", {
            "entry_z": 2.5,
            "exit_z": 0.5,
            "exclude_upbit_binance": True
        }),
        ("전략 4: 진입 강화 + 청산 조정 + 제외", {
            "entry_z": 2.5,
            "exit_z": 0.0,
            "exclude_upbit_binance": True
        }),
    ]
    
    results = []
    for name, params in strategies:
        try:
            metrics = test_strategy(name, **params)
            results.append({
                "전략": name,
                "거래 횟수": metrics['total_trades'],
                "최종 수익률": metrics['final_return'] * 100,
                "승률": metrics['win_rate'] * 100,
                "Sharpe": metrics['sharpe_ratio'],
                "MDD": metrics['mdd'] * 100,
                "초과 수익률": metrics['excess_return'] * 100
            })
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    
    # 결과 비교
    print("\n" + "="*60)
    print("전략 비교")
    print("="*60)
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    # 최고 성과 전략
    if len(results) > 0:
        best = results_df.loc[results_df['최종 수익률'].idxmax()]
        print(f"\n✅ 최고 성과 전략: {best['전략']}")
        print(f"   최종 수익률: {best['최종 수익률']:.2f}%")
        print(f"   승률: {best['승률']:.1f}%")
        print(f"   Sharpe: {best['Sharpe']:.2f}")

if __name__ == "__main__":
    main()

