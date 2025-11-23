#!/usr/bin/env python3
"""
Project 2: 최종 최적화된 차익거래 백테스트 실행
- 최고 성과 전략: 진입 강화 (Z-Score > 2.5) + upbit_binance 제외
"""

from datetime import datetime
from backtest_engine_optimized import OptimizedArbitrageBacktest
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def main():
    START_DATE = "2024-01-01"
    END_DATE = "2025-11-22"
    INITIAL_CAPITAL = 100_000_000
    
    print("🚀 Project 2: 최종 최적화된 차익거래 백테스트")
    print("=" * 60)
    print(f"기간: {START_DATE} ~ {END_DATE}")
    print(f"초기 자본: {INITIAL_CAPITAL:,} KRW")
    print(f"전략: 진입 강화 (Z-Score > 2.5) + upbit_binance 제외")
    print("=" * 60)
    
    backtest = OptimizedArbitrageBacktest(
        initial_capital=INITIAL_CAPITAL,
        entry_z=2.5,  # 강화된 진입 조건
        exit_z=0.5,   # 기존 청산 조건
        exclude_upbit_binance=True  # upbit_binance 제외
    )
    
    # 데이터 로드
    print("\n📊 데이터 로드 중...")
    df = backtest.load_data(START_DATE, END_DATE)
    print(f"   ✅ {len(df)}건 로드 완료")
    
    # 지표 계산
    print("\n📈 지표 계산 중...")
    df = backtest.calculate_indicators(df)
    print(f"   ✅ {len(df)}건 계산 완료")
    
    # 벤치마크 계산
    print("\n📊 벤치마크 계산 중...")
    benchmark_return = backtest.calculate_benchmark(df)
    print(f"   ✅ Buy & Hold 수익률: {benchmark_return * 100:.2f}%")
    
    # 시그널 생성
    print("\n🎯 시그널 생성 중...")
    df = backtest.generate_signals(df)
    signal_count = (df['signal'] != 0).sum()
    print(f"   ✅ {signal_count}개 시그널 생성")
    
    # 백테스트 실행
    print("\n⚙️ 백테스트 실행 중...")
    trades_df, daily_capital_df = backtest.run_backtest(df)
    print(f"   ✅ {len(trades_df)}건 거래 완료")
    
    # 성과 분석
    print("\n📊 성과 분석 중...")
    metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📈 최종 백테스트 결과 리포트")
    print("=" * 60)
    print(f"총 거래 횟수: {metrics['total_trades']}회")
    print(f"최종 수익률: {metrics['final_return'] * 100:.2f}%")
    print(f"연율화 수익률: {metrics['annualized_return'] * 100:.2f}%")
    print(f"총 수익금: {daily_capital_df['capital'].iloc[-1] - INITIAL_CAPITAL:,.0f} KRW")
    print(f"승률: {metrics['win_rate'] * 100:.1f}%")
    print(f"MDD: {metrics['mdd'] * 100:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"평균 보유 기간: {metrics['avg_holding_days']:.1f}일")
    print(f"최대 보유 기간: {metrics['max_holding_days']}일")
    print("-" * 60)
    print(f"벤치마크 (Buy & Hold): {metrics['benchmark_return'] * 100:.2f}%")
    print(f"초과 수익률: {metrics['excess_return'] * 100:.2f}%")
    print("=" * 60)
    
    # 거래소 쌍별 통계
    if not trades_df.empty:
        print("\n📊 거래소 쌍별 통계:")
        pair_stats = trades_df.groupby('pair').agg({
            'return': ['count', 'mean', lambda x: (x > 0).mean()],
            'profit': 'sum',
            'holding_days': 'mean'
        })
        print(pair_stats)
        
        # 청산 사유별 통계
        print("\n📊 청산 사유별 통계:")
        exit_reason_stats = trades_df.groupby('exit_reason').agg({
            'return': ['count', 'mean'],
            'profit': 'sum'
        })
        print(exit_reason_stats)
    
    # 파일 저장
    output_dir = ROOT / "data"
    output_dir.mkdir(exist_ok=True)
    
    trades_df.to_csv(output_dir / "project2_final_trades.csv", index=False)
    daily_capital_df.to_csv(output_dir / "project2_final_daily_capital.csv", index=False)
    
    print(f"\n💾 결과 저장 완료:")
    print(f"   - {output_dir / 'project2_final_trades.csv'}")
    print(f"   - {output_dir / 'project2_final_daily_capital.csv'}")
    
    # 결론
    print("\n" + "=" * 60)
    if metrics['final_return'] > 0:
        print("✅ 전략 성공: 플러스 수익률 달성")
    else:
        print("❌ 전략 실패: 마이너스 수익률")
    
    if metrics['excess_return'] > 0:
        print("✅ 벤치마크 대비 우수: 초과 수익률 달성")
    else:
        print("⚠️ 벤치마크 대비 부진: 초과 수익률 미달")
    print("=" * 60)

if __name__ == "__main__":
    main()

