#!/usr/bin/env python3
"""
Project 2: 개선된 차익거래 백테스트 실행
"""

from datetime import datetime
from backtest_engine_improved import ImprovedArbitrageBacktest
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def main():
    # 2024-01-01부터 현재까지 (3개 거래소 모두 데이터 있음)
    START_DATE = "2024-01-01"
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    INITIAL_CAPITAL = 100_000_000
    FEE_RATE = 0.0005
    SLIPPAGE = 0.0002
    STOP_LOSS = -0.03  # -3%
    MAX_HOLDING_DAYS = 30
    
    print("🚀 Project 2: 개선된 차익거래 백테스트 시작")
    print("=" * 60)
    print(f"기간: {START_DATE} ~ {END_DATE}")
    print(f"초기 자본: {INITIAL_CAPITAL:,} KRW")
    print(f"수수료: {FEE_RATE * 100:.2f}%, 슬리피지: {SLIPPAGE * 100:.2f}%")
    print(f"손절매: {STOP_LOSS * 100:.1f}%, 최대 보유 기간: {MAX_HOLDING_DAYS}일")
    print("=" * 60)
    
    backtest = ImprovedArbitrageBacktest(
        initial_capital=INITIAL_CAPITAL,
        fee_rate=FEE_RATE,
        slippage=SLIPPAGE,
        stop_loss=STOP_LOSS,
        max_holding_days=MAX_HOLDING_DAYS
    )
    
    # 1. 데이터 로드
    print("\n📊 1단계: 데이터 로드")
    df = backtest.load_data(START_DATE, END_DATE)
    print(f"   ✅ {len(df)}건 로드 완료")
    
    if len(df) < 30:
        print("⚠️ 데이터 부족으로 백테스트 중단")
        return
    
    # 2. 지표 계산
    print("\n📈 2단계: 지표 계산 (Look-ahead Bias 제거)")
    df = backtest.calculate_indicators(df)
    print(f"   ✅ {len(df)}건 계산 완료 (첫 30일 제외)")
    
    # 3. 벤치마크 계산
    print("\n📊 3단계: 벤치마크 계산")
    benchmark_return = backtest.calculate_benchmark(df)
    print(f"   ✅ Buy & Hold 수익률: {benchmark_return * 100:.2f}%")
    
    # 4. 시그널 생성
    print("\n🎯 4단계: 시그널 생성")
    df = backtest.generate_signals(df, entry_z=2.0, exit_z=0.5)
    signal_count = (df['signal'] != 0).sum()
    print(f"   ✅ {signal_count}개 시그널 생성")
    
    # 5. 백테스트 실행
    print("\n⚙️ 5단계: 백테스트 실행 (리스크 관리 포함)")
    trades_df, daily_capital_df = backtest.run_backtest(df)
    print(f"   ✅ {len(trades_df)}건 거래 완료")
    
    # 6. 성과 분석
    print("\n📊 6단계: 성과 분석")
    metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📈 백테스트 결과 리포트")
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
    
    trades_df.to_csv(output_dir / "project2_improved_trades.csv", index=False)
    daily_capital_df.to_csv(output_dir / "project2_improved_daily_capital.csv", index=False)
    
    print(f"\n💾 결과 저장 완료:")
    print(f"   - {output_dir / 'project2_improved_trades.csv'}")
    print(f"   - {output_dir / 'project2_improved_daily_capital.csv'}")

if __name__ == "__main__":
    main()

