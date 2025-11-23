#!/usr/bin/env python3
"""
Project 2 최종 통합 테스트
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))

from backtest_engine_improved import ImprovedArbitrageBacktest

def test_data_completeness():
    """통합 테스트 1: 데이터 완전성"""
    print("=" * 60)
    print("통합 테스트 1: 데이터 완전성")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    # 비트겟 데이터가 있는 기간으로 조정 (2025-11-22까지)
    end_date = "2025-11-22"
    df = backtest.load_data("2024-01-01", end_date)
    
    # 모든 거래소 데이터 확인 (NULL 허용하지 않음)
    upbit_missing = df['upbit_price'].isnull().sum()
    binance_missing = df['binance_price'].isnull().sum()
    bitget_missing = df['bitget_price'].isnull().sum()
    krw_usd_missing = df['krw_usd'].isnull().sum()
    
    assert upbit_missing == 0, f"업비트 데이터 누락: {upbit_missing}건"
    assert binance_missing == 0, f"바이낸스 데이터 누락: {binance_missing}건"
    assert bitget_missing == 0, f"비트겟 데이터 누락: {bitget_missing}건"
    assert krw_usd_missing == 0, f"환율 데이터 누락: {krw_usd_missing}건"
    
    print(f"✅ 데이터 완전성 확인: {len(df)}건")
    print(f"   업비트 누락: {upbit_missing}건")
    print(f"   바이낸스 누락: {binance_missing}건")
    print(f"   비트겟 누락: {bitget_missing}건")
    print(f"   환율 누락: {krw_usd_missing}건")
    return True

def test_end_to_end_backtest():
    """통합 테스트 2: 전체 백테스트 파이프라인"""
    print("\n" + "=" * 60)
    print("통합 테스트 2: 전체 백테스트 파이프라인")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    
    # 전체 파이프라인 실행 (비트겟 데이터가 있는 기간)
    end_date = "2025-11-22"
    df = backtest.load_data("2024-01-01", end_date)
    df = backtest.calculate_indicators(df)
    benchmark_return = backtest.calculate_benchmark(df)
    df = backtest.generate_signals(df, entry_z=2.0, exit_z=0.5)
    trades_df, daily_capital_df = backtest.run_backtest(df)
    metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
    
    # 결과 검증
    assert 'total_trades' in metrics, "total_trades 없음"
    assert 'final_return' in metrics, "final_return 없음"
    assert 'annualized_return' in metrics, "annualized_return 없음"
    assert 'sharpe_ratio' in metrics, "sharpe_ratio 없음"
    assert 'mdd' in metrics, "mdd 없음"
    assert 'benchmark_return' in metrics, "benchmark_return 없음"
    
    print(f"✅ 전체 파이프라인 실행 성공")
    print(f"   거래 횟수: {metrics['total_trades']}회")
    print(f"   최종 수익률: {metrics['final_return'] * 100:.2f}%")
    print(f"   연율화 수익률: {metrics['annualized_return'] * 100:.2f}%")
    return True

def test_risk_management_integration():
    """통합 테스트 3: 리스크 관리 통합"""
    print("\n" + "=" * 60)
    print("통합 테스트 3: 리스크 관리 통합")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest(
        stop_loss=-0.03,
        max_holding_days=30
    )
    
    end_date = "2025-11-22"
    df = backtest.load_data("2024-01-01", end_date)
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0, exit_z=0.5)
    trades_df, daily_capital_df = backtest.run_backtest(df)
    
    if not trades_df.empty:
        # 최대 보유 기간 확인
        max_holding = trades_df['holding_days'].max()
        assert max_holding <= 30, f"최대 보유 기간 초과: {max_holding}일"
        
        # 손절매 확인
        stop_loss_count = (trades_df['exit_reason'] == 'stop_loss').sum()
        max_holding_count = (trades_df['exit_reason'] == 'max_holding_days').sum()
        
        print(f"✅ 리스크 관리 통합 확인")
        print(f"   최대 보유 기간: {max_holding}일 (제한: 30일)")
        print(f"   손절매 거래: {stop_loss_count}건")
        print(f"   최대 보유 기간 초과: {max_holding_count}건")
    else:
        print("⚠️ 거래가 발생하지 않아 리스크 관리 테스트를 건너뜁니다")
    
    return True

def test_daily_capital_curve_integration():
    """통합 테스트 4: 일별 자본 곡선 통합"""
    print("\n" + "=" * 60)
    print("통합 테스트 4: 일별 자본 곡선 통합")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    
    end_date = "2025-11-22"
    df = backtest.load_data("2024-01-01", end_date)
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0, exit_z=0.5)
    trades_df, daily_capital_df = backtest.run_backtest(df)
    
    # 일별 자본 곡선 검증
    assert len(daily_capital_df) > 0, "일별 자본 곡선이 없습니다"
    assert daily_capital_df['capital'].iloc[0] == backtest.initial_capital, "초기 자본 불일치"
    assert daily_capital_df['capital'].min() > 0, "자본이 0 이하입니다"
    
    # MDD 계산 검증
    daily_capital_df['peak'] = daily_capital_df['capital'].cummax()
    daily_capital_df['drawdown'] = (daily_capital_df['capital'] - daily_capital_df['peak']) / daily_capital_df['peak']
    mdd = daily_capital_df['drawdown'].min()
    
    assert mdd <= 0, "MDD가 0보다 큽니다"
    
    print(f"✅ 일별 자본 곡선 통합 확인")
    print(f"   총 일수: {len(daily_capital_df)}일")
    print(f"   최대 MDD: {mdd * 100:.2f}%")
    return True

def test_benchmark_comparison():
    """통합 테스트 5: 벤치마크 비교"""
    print("\n" + "=" * 60)
    print("통합 테스트 5: 벤치마크 비교")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest()
    
    end_date = "2025-11-22"
    df = backtest.load_data("2024-01-01", end_date)
    benchmark_return = backtest.calculate_benchmark(df)
    
    df = backtest.calculate_indicators(df)
    df = backtest.generate_signals(df, entry_z=2.0, exit_z=0.5)
    trades_df, daily_capital_df = backtest.run_backtest(df)
    metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
    
    assert 'benchmark_return' in metrics, "benchmark_return 없음"
    assert 'excess_return' in metrics, "excess_return 없음"
    assert abs(metrics['excess_return'] - (metrics['final_return'] - metrics['benchmark_return'])) < 0.0001, "초과 수익률 계산 오류"
    
    print(f"✅ 벤치마크 비교 확인")
    print(f"   벤치마크 수익률: {metrics['benchmark_return'] * 100:.2f}%")
    print(f"   전략 수익률: {metrics['final_return'] * 100:.2f}%")
    print(f"   초과 수익률: {metrics['excess_return'] * 100:.2f}%")
    return True

def main():
    """모든 통합 테스트 실행"""
    print("🧪 Project 2 최종 통합 테스트 시작\n")
    
    tests = [
        test_data_completeness,
        test_end_to_end_backtest,
        test_risk_management_integration,
        test_daily_capital_curve_integration,
        test_benchmark_comparison
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
    print("통합 테스트 결과")
    print("=" * 60)
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ 모든 통합 테스트 통과!")
        print("✅ Project 2 서비스 구현 완료!")
    else:
        print("\n❌ 일부 테스트 실패. 위 결과를 확인하세요.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

