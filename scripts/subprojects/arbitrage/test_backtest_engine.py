#!/usr/bin/env python3
"""
백테스트 엔진 유닛 테스트
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))

from backtest_engine_improved import ImprovedArbitrageBacktest

def test_load_data():
    """테스트 1: 데이터 로드"""
    print("=" * 60)
    print("테스트 1: 데이터 로드")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    df = backtest.load_data("2024-01-01", "2024-01-31")
    
    assert len(df) > 0, "데이터가 로드되지 않았습니다"
    assert 'upbit_price' in df.columns, "upbit_price 컬럼이 없습니다"
    assert 'binance_krw' in df.columns, "binance_krw 컬럼이 없습니다"
    assert 'bitget_krw' in df.columns, "bitget_krw 컬럼이 없습니다"
    assert df['krw_usd'].isnull().sum() == 0, "환율 데이터가 누락되었습니다"
    
    print(f"✅ 데이터 로드 성공: {len(df)}건")
    print(f"   날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
    return True

def test_calculate_indicators():
    """테스트 2: 지표 계산 및 Look-ahead Bias 제거"""
    print("\n" + "=" * 60)
    print("테스트 2: 지표 계산 및 Look-ahead Bias 제거")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest(rolling_window=30)
    df = backtest.load_data("2024-01-01", "2024-03-31")
    original_len = len(df)
    
    df = backtest.calculate_indicators(df)
    
    # Look-ahead Bias 제거 확인: 첫 30일이 제외되었는지 확인
    assert len(df) <= original_len - 30, "첫 30일이 제외되지 않았습니다"
    assert df['z_score_upbit_binance'].isnull().sum() == 0, "Z-Score에 NULL이 있습니다"
    assert df['z_score_upbit_bitget'].isnull().sum() == 0, "Z-Score에 NULL이 있습니다"
    assert df['z_score_binance_bitget'].isnull().sum() == 0, "Z-Score에 NULL이 있습니다"
    
    print(f"✅ 지표 계산 성공: {len(df)}건")
    print(f"   원본: {original_len}건, 계산 후: {len(df)}건 (첫 30일 제외)")
    return True

def test_generate_signals():
    """테스트 3: 시그널 생성"""
    print("\n" + "=" * 60)
    print("테스트 3: 시그널 생성")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    df = backtest.load_data("2024-01-01", "2024-03-31")
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0)
    
    assert 'signal' in df.columns, "signal 컬럼이 없습니다"
    assert 'signal_pair' in df.columns, "signal_pair 컬럼이 없습니다"
    assert 'signal_direction' in df.columns, "signal_direction 컬럼이 없습니다"
    
    signal_count = (df['signal'] != 0).sum()
    print(f"✅ 시그널 생성 성공: {signal_count}개 시그널 생성")
    return True

def test_risk_management():
    """테스트 4: 리스크 관리 (손절매, 최대 보유 기간)"""
    print("\n" + "=" * 60)
    print("테스트 4: 리스크 관리")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest(
        stop_loss=-0.03,  # -3%
        max_holding_days=30
    )
    
    df = backtest.load_data("2024-01-01", "2024-06-30")
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0)
    
    trades_df, daily_capital_df = backtest.run_backtest(df)
    
    if not trades_df.empty:
        # 손절매 확인
        stop_loss_trades = trades_df[trades_df['exit_reason'] == 'stop_loss']
        max_holding_trades = trades_df[trades_df['exit_reason'] == 'max_holding_days']
        
        print(f"✅ 리스크 관리 작동 확인:")
        print(f"   손절매 거래: {len(stop_loss_trades)}건")
        print(f"   최대 보유 기간 초과: {len(max_holding_trades)}건")
        
        # 최대 보유 기간 확인
        if len(trades_df) > 0:
            max_holding = trades_df['holding_days'].max()
            assert max_holding <= 30, f"최대 보유 기간이 30일을 초과했습니다: {max_holding}일"
            print(f"   실제 최대 보유 기간: {max_holding}일")
    else:
        print("⚠️ 거래가 발생하지 않아 리스크 관리 테스트를 건너뜁니다")
    
    return True

def test_daily_capital_curve():
    """테스트 5: 일별 자본 곡선"""
    print("\n" + "=" * 60)
    print("테스트 5: 일별 자본 곡선")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    df = backtest.load_data("2024-01-01", "2024-06-30")
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0)
    
    trades_df, daily_capital_df = backtest.run_backtest(df)
    
    assert len(daily_capital_df) > 0, "일별 자본 곡선이 생성되지 않았습니다"
    assert 'date' in daily_capital_df.columns, "date 컬럼이 없습니다"
    assert 'capital' in daily_capital_df.columns, "capital 컬럼이 없습니다"
    assert daily_capital_df['capital'].iloc[0] == backtest.initial_capital, "초기 자본이 올바르지 않습니다"
    
    print(f"✅ 일별 자본 곡선 생성 성공: {len(daily_capital_df)}일")
    print(f"   초기 자본: {daily_capital_df['capital'].iloc[0]:,.0f}")
    print(f"   최종 자본: {daily_capital_df['capital'].iloc[-1]:,.0f}")
    return True

def test_performance_metrics():
    """테스트 6: 성과 지표 계산"""
    print("\n" + "=" * 60)
    print("테스트 6: 성과 지표 계산")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    df = backtest.load_data("2024-01-01", "2024-06-30")
    benchmark_return = backtest.calculate_benchmark(df)
    
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0)
    
    trades_df, daily_capital_df = backtest.run_backtest(df)
    metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
    
    assert 'annualized_return' in metrics, "annualized_return이 없습니다"
    assert 'sharpe_ratio' in metrics, "sharpe_ratio가 없습니다"
    assert 'mdd' in metrics, "mdd가 없습니다"
    assert 'benchmark_return' in metrics, "benchmark_return이 없습니다"
    assert 'excess_return' in metrics, "excess_return이 없습니다"
    
    print(f"✅ 성과 지표 계산 성공:")
    print(f"   최종 수익률: {metrics['final_return'] * 100:.2f}%")
    print(f"   연율화 수익률: {metrics['annualized_return'] * 100:.2f}%")
    print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"   MDD: {metrics['mdd'] * 100:.2f}%")
    print(f"   벤치마크 수익률: {metrics['benchmark_return'] * 100:.2f}%")
    print(f"   초과 수익률: {metrics['excess_return'] * 100:.2f}%")
    return True

def main():
    """모든 테스트 실행"""
    print("🧪 백테스트 엔진 유닛 테스트 시작\n")
    
    tests = [
        test_load_data,
        test_calculate_indicators,
        test_generate_signals,
        test_risk_management,
        test_daily_capital_curve,
        test_performance_metrics
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} 실패")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("테스트 결과")
    print("=" * 60)
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

