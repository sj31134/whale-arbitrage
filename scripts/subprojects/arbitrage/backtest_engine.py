"""
Project 2: Arbitrage Backtest Engine
- Load data from SQLite
- Calculate Premium & Z-Score
- Generate Signals
- Execute Backtest
- Calculate Performance Metrics
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


class ArbitrageBacktest:
    def __init__(self, initial_capital=100_000_000, fee_rate=0.0005, slippage=0.0002):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.conn = sqlite3.connect(DB_PATH)

    def load_data(self, start_date, end_date):
        """데이터 로드 및 병합"""
        query = f"""
        SELECT 
            u.date,
            u.trade_price as upbit_price,
            b.close as binance_price,
            e.krw_usd
        FROM upbit_daily u
        JOIN binance_spot_daily b ON u.date = b.date
        LEFT JOIN exchange_rate e ON u.date = e.date
        WHERE u.market = 'KRW-BTC' AND b.symbol = 'BTCUSDT'
        AND u.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY u.date
        """
        df = pd.read_sql(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        
        # 환율 결측치 처리 (전일 값으로 채움)
        df['krw_usd'] = df['krw_usd'].ffill()
        
        return df

    def calculate_indicators(self, df):
        """지표 계산 (괴리율, Z-Score)"""
        df = df.copy()
        
        # 김치 프리미엄 계산
        df['binance_krw'] = df['binance_price'] * df['krw_usd']
        df['premium'] = (df['upbit_price'] - df['binance_krw']) / df['binance_krw']
        
        # Z-Score (30일 이동평균 기준)
        df['premium_mean'] = df['premium'].rolling(window=30).mean()
        df['premium_std'] = df['premium'].rolling(window=30).std()
        df['z_score'] = (df['premium'] - df['premium_mean']) / df['premium_std']
        
        return df.dropna()

    def generate_signals(self, df, entry_z=2.0, exit_z=0.5):
        """시그널 생성"""
        df = df.copy()
        df['signal'] = 0
        
        # 진입: Z-Score > 2.0 (김프 과대 -> 업비트 매도 / 바이낸스 매수)
        # 여기서는 "괴리율 축소"에 베팅하는 구조
        # 실제로는: 업비트 공매도 불가능하므로, 보유 BTC 매도 or 선물 매도 포지션 가정 필요
        # 이 백테스트는 "양방향 매매가 가능하다"는 가정 하에 논리적 수익성을 검증함
        
        # Signal 1: Short Premium (Sell Upbit, Buy Binance)
        df.loc[df['z_score'] > entry_z, 'signal'] = 1
        
        # Signal -1: Long Premium (Buy Upbit, Sell Binance) -> 역프/저평가 시
        df.loc[df['z_score'] < -entry_z, 'signal'] = -1
        
        # Exit: Z-Score 회귀 시 (0.5 미만)
        # 포지션 관리는 run_backtest에서 수행
        
        return df

    def run_backtest(self, df):
        """백테스트 실행"""
        position = 0 # 0: None, 1: Short Premium, -1: Long Premium
        capital = self.initial_capital
        history = []
        
        entry_price_upbit = 0
        entry_price_binance = 0
        entry_date = None
        
        # 수수료/슬리피지 비용 비율 (진입+청산 시 각각 발생)
        cost_rate = self.fee_rate + self.slippage
        
        for idx, row in df.iterrows():
            current_signal = row['signal']
            z_score = row['z_score']
            
            # 포지션 진입 로직
            if position == 0:
                if current_signal == 1:
                    # Short Premium 진입
                    position = 1
                    entry_price_upbit = row['upbit_price']
                    entry_price_binance = row['binance_krw'] # 원화 환산가 기준 진입 가정
                    entry_date = row['date']
                    
                elif current_signal == -1:
                    # Long Premium 진입
                    position = -1
                    entry_price_upbit = row['upbit_price']
                    entry_price_binance = row['binance_krw']
                    entry_date = row['date']
            
            # 포지션 청산 로직 (평균 회귀)
            elif position == 1:
                # Short Premium 청산 조건: Z-Score < 0.5
                if z_score < 0.5:
                    # 수익 계산: 
                    # 업비트: (진입 - 현재) / 진입  (매도 포지션 이익)
                    # 바이낸스: (현재 - 진입) / 진입 (매수 포지션 이익)
                    
                    ret_upbit = (entry_price_upbit - row['upbit_price']) / entry_price_upbit
                    ret_binance = (row['binance_krw'] - entry_price_binance) / entry_price_binance
                    
                    # 총 수익률 (레버리지 1배 가정, 자본 50:50 분할)
                    gross_return = (ret_upbit + ret_binance) / 2
                    net_return = gross_return - (cost_rate * 2) # 진입/청산 비용 2회
                    
                    profit = capital * net_return
                    capital += profit
                    
                    history.append({
                        'entry_date': entry_date,
                        'exit_date': row['date'],
                        'position': 'Short Premium',
                        'return': net_return,
                        'profit': profit,
                        'capital': capital
                    })
                    position = 0
                    
            elif position == -1:
                # Long Premium 청산 조건: Z-Score > -0.5
                if z_score > -0.5:
                    # 수익 계산:
                    # 업비트: (현재 - 진입) / 진입 (매수 포지션 이익)
                    # 바이낸스: (진입 - 현재) / 진입 (매도 포지션 이익)
                    
                    ret_upbit = (row['upbit_price'] - entry_price_upbit) / entry_price_upbit
                    ret_binance = (entry_price_binance - row['binance_krw']) / entry_price_binance
                    
                    gross_return = (ret_upbit + ret_binance) / 2
                    net_return = gross_return - (cost_rate * 2)
                    
                    profit = capital * net_return
                    capital += profit
                    
                    history.append({
                        'entry_date': entry_date,
                        'exit_date': row['date'],
                        'position': 'Long Premium',
                        'return': net_return,
                        'profit': profit,
                        'capital': capital
                    })
                    position = 0
                    
        return pd.DataFrame(history)

    def analyze_performance(self, trade_df):
        """성과 분석"""
        if trade_df.empty:
            return {
                "total_trades": 0,
                "final_return": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "mdd": 0.0
            }
            
        total_trades = len(trade_df)
        final_return = (trade_df['capital'].iloc[-1] - self.initial_capital) / self.initial_capital
        
        # 승률
        win_rate = (trade_df['return'] > 0).mean()
        
        # MDD (자본금 기준)
        capital_curve = trade_df['capital']
        peak = capital_curve.cummax()
        drawdown = (capital_curve - peak) / peak
        mdd = drawdown.min()
        
        # Sharpe (간단 계산: 평균 수익률 / 표준편차) * sqrt(거래횟수) -> 연율화 필요하지만 여기선 단순화
        if trade_df['return'].std() == 0:
            sharpe = 0
        else:
            sharpe = (trade_df['return'].mean() / trade_df['return'].std()) * np.sqrt(total_trades)
            
        return {
            "total_trades": total_trades,
            "final_return": final_return,
            "sharpe_ratio": sharpe,
            "win_rate": win_rate,
            "mdd": mdd
        }

