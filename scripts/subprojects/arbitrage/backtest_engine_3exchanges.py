"""
Project 2: Arbitrage Backtest Engine (3 Exchanges)
- Load data from SQLite (Upbit, Binance, Bitget)
- Calculate Premium & Z-Score for each exchange pair
- Generate Signals (best arbitrage opportunity)
- Execute Backtest
- Calculate Performance Metrics
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


class ArbitrageBacktest3Exchanges:
    def __init__(self, initial_capital=100_000_000, fee_rate=0.0005, slippage=0.0002):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.conn = sqlite3.connect(DB_PATH)

    def load_data(self, start_date, end_date):
        """3개 거래소 데이터 로드 및 병합"""
        query = f"""
        SELECT 
            u.date,
            u.trade_price as upbit_price,
            b.close as binance_price,
            bg.close as bitget_price,
            e.krw_usd
        FROM upbit_daily u
        LEFT JOIN binance_spot_daily b ON u.date = b.date AND b.symbol = 'BTCUSDT'
        LEFT JOIN bitget_spot_daily bg ON u.date = bg.date AND bg.symbol = 'BTCUSDT'
        LEFT JOIN exchange_rate e ON u.date = e.date
        WHERE u.market = 'KRW-BTC'
        AND u.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY u.date
        """
        df = pd.read_sql(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        
        # 환율 결측치 처리 (전일 값으로 채움)
        df['krw_usd'] = df['krw_usd'].ffill()
        
        # USDT 가격을 원화로 환산
        df['binance_krw'] = df['binance_price'] * df['krw_usd']
        df['bitget_krw'] = df['bitget_price'] * df['krw_usd']
        
        return df

    def calculate_indicators(self, df):
        """각 거래소 쌍별 프리미엄 및 Z-Score 계산"""
        df = df.copy()
        
        # 1. 업비트 vs 바이낸스 프리미엄
        df['premium_upbit_binance'] = (df['upbit_price'] - df['binance_krw']) / df['binance_krw']
        df['premium_upbit_binance_mean'] = df['premium_upbit_binance'].rolling(window=30).mean()
        df['premium_upbit_binance_std'] = df['premium_upbit_binance'].rolling(window=30).std()
        df['z_score_upbit_binance'] = (
            (df['premium_upbit_binance'] - df['premium_upbit_binance_mean']) 
            / df['premium_upbit_binance_std']
        )
        
        # 2. 업비트 vs 비트겟 프리미엄
        df['premium_upbit_bitget'] = (df['upbit_price'] - df['bitget_krw']) / df['bitget_krw']
        df['premium_upbit_bitget_mean'] = df['premium_upbit_bitget'].rolling(window=30).mean()
        df['premium_upbit_bitget_std'] = df['premium_upbit_bitget'].rolling(window=30).std()
        df['z_score_upbit_bitget'] = (
            (df['premium_upbit_bitget'] - df['premium_upbit_bitget_mean']) 
            / df['premium_upbit_bitget_std']
        )
        
        # 3. 바이낸스 vs 비트겟 프리미엄
        df['premium_binance_bitget'] = (df['binance_krw'] - df['bitget_krw']) / df['bitget_krw']
        df['premium_binance_bitget_mean'] = df['premium_binance_bitget'].rolling(window=30).mean()
        df['premium_binance_bitget_std'] = df['premium_binance_bitget'].rolling(window=30).std()
        df['z_score_binance_bitget'] = (
            (df['premium_binance_bitget'] - df['premium_binance_bitget_mean']) 
            / df['premium_binance_bitget_std']
        )
        
        return df.dropna()

    def generate_signals(self, df, entry_z=2.0, exit_z=0.5):
        """최적의 차익거래 기회 선택"""
        df = df.copy()
        df['signal'] = 0
        df['signal_pair'] = None  # 'upbit_binance', 'upbit_bitget', 'binance_bitget'
        df['signal_direction'] = None  # 'short_premium', 'long_premium'
        
        for idx, row in df.iterrows():
            # 각 쌍의 Z-Score 절댓값 계산
            z_scores = {
                'upbit_binance': abs(row['z_score_upbit_binance']),
                'upbit_bitget': abs(row['z_score_upbit_bitget']),
                'binance_bitget': abs(row['z_score_binance_bitget'])
            }
            
            # 가장 큰 Z-Score를 가진 쌍 선택
            best_pair = max(z_scores, key=z_scores.get)
            best_z = z_scores[best_pair]
            
            # 진입 조건: Z-Score > entry_z
            if best_z > entry_z:
                if best_pair == 'upbit_binance':
                    z_score = row['z_score_upbit_binance']
                    if z_score > entry_z:
                        df.at[idx, 'signal'] = 1
                        df.at[idx, 'signal_pair'] = 'upbit_binance'
                        df.at[idx, 'signal_direction'] = 'short_premium'  # 업비트 매도, 바이낸스 매수
                    elif z_score < -entry_z:
                        df.at[idx, 'signal'] = -1
                        df.at[idx, 'signal_pair'] = 'upbit_binance'
                        df.at[idx, 'signal_direction'] = 'long_premium'  # 업비트 매수, 바이낸스 매도
                        
                elif best_pair == 'upbit_bitget':
                    z_score = row['z_score_upbit_bitget']
                    if z_score > entry_z:
                        df.at[idx, 'signal'] = 1
                        df.at[idx, 'signal_pair'] = 'upbit_bitget'
                        df.at[idx, 'signal_direction'] = 'short_premium'  # 업비트 매도, 비트겟 매수
                    elif z_score < -entry_z:
                        df.at[idx, 'signal'] = -1
                        df.at[idx, 'signal_pair'] = 'upbit_bitget'
                        df.at[idx, 'signal_direction'] = 'long_premium'  # 업비트 매수, 비트겟 매도
                        
                elif best_pair == 'binance_bitget':
                    z_score = row['z_score_binance_bitget']
                    if z_score > entry_z:
                        df.at[idx, 'signal'] = 1
                        df.at[idx, 'signal_pair'] = 'binance_bitget'
                        df.at[idx, 'signal_direction'] = 'short_premium'  # 바이낸스 매도, 비트겟 매수
                    elif z_score < -entry_z:
                        df.at[idx, 'signal'] = -1
                        df.at[idx, 'signal_pair'] = 'binance_bitget'
                        df.at[idx, 'signal_direction'] = 'long_premium'  # 바이낸스 매수, 비트겟 매도
        
        return df

    def run_backtest(self, df):
        """백테스트 실행"""
        position = 0  # 0: None, 1: Short Premium, -1: Long Premium
        position_pair = None
        capital = self.initial_capital
        history = []
        
        entry_price_high = 0  # 높은 가격 거래소
        entry_price_low = 0   # 낮은 가격 거래소
        entry_date = None
        
        cost_rate = self.fee_rate + self.slippage
        
        for idx, row in df.iterrows():
            current_signal = row['signal']
            current_pair = row['signal_pair']
            current_direction = row['signal_direction']
            
            # 포지션 진입 로직
            if position == 0:
                if current_signal != 0 and current_pair:
                    position = current_signal
                    position_pair = current_pair
                    entry_date = row['date']
                    
                    # 진입 가격 설정
                    if current_pair == 'upbit_binance':
                        if current_direction == 'short_premium':
                            entry_price_high = row['upbit_price']
                            entry_price_low = row['binance_krw']
                        else:  # long_premium
                            entry_price_high = row['binance_krw']
                            entry_price_low = row['upbit_price']
                            
                    elif current_pair == 'upbit_bitget':
                        if current_direction == 'short_premium':
                            entry_price_high = row['upbit_price']
                            entry_price_low = row['bitget_krw']
                        else:  # long_premium
                            entry_price_high = row['bitget_krw']
                            entry_price_low = row['upbit_price']
                            
                    elif current_pair == 'binance_bitget':
                        if current_direction == 'short_premium':
                            entry_price_high = row['binance_krw']
                            entry_price_low = row['bitget_krw']
                        else:  # long_premium
                            entry_price_high = row['bitget_krw']
                            entry_price_low = row['binance_krw']
            
            # 포지션 청산 로직
            elif position != 0:
                # 현재 가격 가져오기
                if position_pair == 'upbit_binance':
                    current_price_high = row['upbit_price'] if position == 1 else row['binance_krw']
                    current_price_low = row['binance_krw'] if position == 1 else row['upbit_price']
                    z_score = row['z_score_upbit_binance']
                    
                elif position_pair == 'upbit_bitget':
                    current_price_high = row['upbit_price'] if position == 1 else row['bitget_krw']
                    current_price_low = row['bitget_krw'] if position == 1 else row['upbit_price']
                    z_score = row['z_score_upbit_bitget']
                    
                elif position_pair == 'binance_bitget':
                    current_price_high = row['binance_krw'] if position == 1 else row['bitget_krw']
                    current_price_low = row['bitget_krw'] if position == 1 else row['binance_krw']
                    z_score = row['z_score_binance_bitget']
                else:
                    continue
                
                # 청산 조건: Z-Score 회귀 (절댓값 < exit_z)
                if abs(z_score) < 0.5:
                    # 수익 계산
                    ret_high = (entry_price_high - current_price_high) / entry_price_high if position == 1 else (current_price_high - entry_price_high) / entry_price_high
                    ret_low = (current_price_low - entry_price_low) / entry_price_low if position == 1 else (entry_price_low - current_price_low) / entry_price_low
                    
                    gross_return = (ret_high + ret_low) / 2
                    net_return = gross_return - (cost_rate * 2)
                    
                    profit = capital * net_return
                    capital += profit
                    
                    history.append({
                        'entry_date': entry_date,
                        'exit_date': row['date'],
                        'pair': position_pair,
                        'direction': 'Short Premium' if position == 1 else 'Long Premium',
                        'return': net_return,
                        'profit': profit,
                        'capital': capital
                    })
                    
                    position = 0
                    position_pair = None
        
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
        
        win_rate = (trade_df['return'] > 0).mean()
        
        capital_curve = trade_df['capital']
        peak = capital_curve.cummax()
        drawdown = (capital_curve - peak) / peak
        mdd = drawdown.min()
        
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

