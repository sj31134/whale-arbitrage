#!/usr/bin/env python3
"""
Project 2 Backtest Runner
"""

from backtest_engine import ArbitrageBacktest
from datetime import datetime

def main():
    print("🚀 Project 2: Arbitrage Backtest 시작")
    
    # 설정
    START_DATE = "2023-01-01"
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    INITIAL_CAPITAL = 100_000_000
    
    engine = ArbitrageBacktest(initial_capital=INITIAL_CAPITAL)
    
    # 1. 데이터 로드
    print(f"📊 데이터 로드 중 ({START_DATE} ~ {END_DATE})...")
    df = engine.load_data(START_DATE, END_DATE)
    print(f"   - {len(df)}건 로드 완료")
    
    if len(df) < 30:
        print("⚠️ 데이터 부족으로 백테스트 중단")
        return
        
    # 2. 지표 계산
    df = engine.calculate_indicators(df)
    
    # 3. 시그널 생성
    df = engine.generate_signals(df)
    
    # 4. 백테스트 실행
    trades = engine.run_backtest(df)
    
    # 5. 결과 분석
    perf = engine.analyze_performance(trades)
    
    print("\n" + "="*40)
    print("📈 백테스트 결과 리포트")
    print("="*40)
    print(f"총 거래 횟수: {perf['total_trades']}회")
    print(f"최종 수익률: {perf['final_return']*100:.2f}%")
    print(f"총 수익금: {perf['final_return']*INITIAL_CAPITAL:,.0f} KRW")
    print(f"승률: {perf['win_rate']*100:.1f}%")
    print(f"MDD: {perf['mdd']*100:.2f}%")
    print(f"Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
    print("="*40)
    
    # 거래 내역 저장
    trades.to_csv("data/project2_backtest_trades.csv", index=False)
    print(f"\n💾 거래 내역 저장 완료: data/project2_backtest_trades.csv")

if __name__ == "__main__":
    main()

