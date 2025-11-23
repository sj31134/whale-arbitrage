#!/usr/bin/env python3
"""
Project 2: 3개 거래소 차익거래 백테스트 실행
"""

from datetime import datetime
from backtest_engine_3exchanges import ArbitrageBacktest3Exchanges
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def main():
    # 비트겟 데이터가 있는 기간으로 조정 (2025-05-07부터)
    START_DATE = "2025-05-07"
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    INITIAL_CAPITAL = 100_000_000
    FEE_RATE = 0.0005
    SLIPPAGE = 0.0002
    
    print("🚀 Project 2: 3개 거래소 차익거래 백테스트 시작")
    print(f"   기간: {START_DATE} ~ {END_DATE}")
    print(f"   초기 자본: {INITIAL_CAPITAL:,} KRW")
    
    backtest = ArbitrageBacktest3Exchanges(
        initial_capital=INITIAL_CAPITAL,
        fee_rate=FEE_RATE,
        slippage=SLIPPAGE
    )
    
    # 데이터 로드
    print("📊 데이터 로드 중...")
    df = backtest.load_data(START_DATE, END_DATE)
    print(f"   - {len(df)}건 로드 완료")
    
    # 지표 계산
    print("📈 지표 계산 중...")
    df = backtest.calculate_indicators(df)
    print(f"   - {len(df)}건 계산 완료")
    
    # 시그널 생성
    print("🎯 시그널 생성 중...")
    df = backtest.generate_signals(df, entry_z=2.0, exit_z=0.5)
    
    # 백테스트 실행
    print("⚙️ 백테스트 실행 중...")
    trades_df = backtest.run_backtest(df)
    
    # 성과 분석
    print("\n" + "=" * 40)
    print("📈 백테스트 결과 리포트")
    print("=" * 40)
    
    if trades_df.empty:
        print("⚠️ 거래가 발생하지 않았습니다.")
        return
    
    metrics = backtest.analyze_performance(trades_df)
    
    print(f"총 거래 횟수: {metrics['total_trades']}회")
    print(f"최종 수익률: {metrics['final_return'] * 100:.2f}%")
    print(f"총 수익금: {trades_df['capital'].iloc[-1] - INITIAL_CAPITAL:,.0f} KRW")
    print(f"승률: {metrics['win_rate'] * 100:.1f}%")
    print(f"MDD: {metrics['mdd'] * 100:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    
    # 거래소 쌍별 통계
    print("\n📊 거래소 쌍별 통계:")
    pair_stats = trades_df.groupby('pair').agg({
        'return': ['count', 'mean', lambda x: (x > 0).mean()],
        'profit': 'sum'
    })
    print(pair_stats)
    
    # 거래 내역 저장
    output_path = ROOT / "data" / "project2_backtest_3exchanges_trades.csv"
    trades_df.to_csv(output_path, index=False)
    print(f"\n💾 거래 내역 저장 완료: {output_path}")

if __name__ == "__main__":
    main()

