"""
Project 2: 최적화된 차익거래 백테스트 엔진
- upbit_binance 쌍 제외 또는 조건 강화
- 진입 조건 강화 (Z-Score > 2.5)
- 청산 조건 조정 (Z-Score < 0.0)
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta
import os

# 환경별 경로 설정
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
    DB_PATH = Path('/tmp') / "project.db"
elif os.path.exists('/tmp'):
    # 임시 디렉토리 사용 가능한 환경
    ROOT = Path('/tmp')
    DB_PATH = ROOT / "project.db"
elif os.path.exists('/app'):
    # Docker 컨테이너 내부
    ROOT = Path('/app')
    DB_PATH = ROOT / "data" / "project.db"
else:
    # 로컬 개발 환경
    ROOT = Path(__file__).resolve().parents[3]
    DB_PATH = ROOT / "data" / "project.db"


class OptimizedArbitrageBacktest:
    def __init__(
        self, 
        initial_capital=100_000_000, 
        fee_rate=0.0005, 
        slippage=0.0002,
        stop_loss=-0.03,
        max_holding_days=30,
        rolling_window=30,
        entry_z=2.5,  # 강화된 진입 조건
        exit_z=0.0,   # 조정된 청산 조건
        exclude_upbit_binance=False  # upbit_binance 쌍 제외 옵션
    ):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.stop_loss = stop_loss
        self.max_holding_days = max_holding_days
        self.rolling_window = rolling_window
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.exclude_upbit_binance = exclude_upbit_binance
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
        
        df['krw_usd'] = df['krw_usd'].ffill().bfill()
        df['binance_krw'] = df['binance_price'] * df['krw_usd']
        df['bitget_krw'] = df['bitget_price'] * df['krw_usd']
        
        return df

    def calculate_indicators(self, df):
        """각 거래소 쌍별 프리미엄 및 Z-Score 계산"""
        df = df.copy()
        
        # 1. 업비트 vs 바이낸스 프리미엄
        df['premium_upbit_binance'] = (df['upbit_price'] - df['binance_krw']) / df['binance_krw']
        df['premium_upbit_binance_mean'] = df['premium_upbit_binance'].rolling(window=self.rolling_window).mean()
        df['premium_upbit_binance_std'] = df['premium_upbit_binance'].rolling(window=self.rolling_window).std()
        df['z_score_upbit_binance'] = (
            (df['premium_upbit_binance'] - df['premium_upbit_binance_mean']) 
            / df['premium_upbit_binance_std']
        )
        
        # 2. 업비트 vs 비트겟 프리미엄
        df['premium_upbit_bitget'] = (df['upbit_price'] - df['bitget_krw']) / df['bitget_krw']
        df['premium_upbit_bitget_mean'] = df['premium_upbit_bitget'].rolling(window=self.rolling_window).mean()
        df['premium_upbit_bitget_std'] = df['premium_upbit_bitget'].rolling(window=self.rolling_window).std()
        df['z_score_upbit_bitget'] = (
            (df['premium_upbit_bitget'] - df['premium_upbit_bitget_mean']) 
            / df['premium_upbit_bitget_std']
        )
        
        # 3. 바이낸스 vs 비트겟 프리미엄
        df['premium_binance_bitget'] = (df['binance_krw'] - df['bitget_krw']) / df['bitget_krw']
        df['premium_binance_bitget_mean'] = df['premium_binance_bitget'].rolling(window=self.rolling_window).mean()
        df['premium_binance_bitget_std'] = df['premium_binance_bitget'].rolling(window=self.rolling_window).std()
        df['z_score_binance_bitget'] = (
            (df['premium_binance_bitget'] - df['premium_binance_bitget_mean']) 
            / df['premium_binance_bitget_std']
        )
        
        # NULL 값 처리: 핵심 가격 데이터만 확인
        # exchange_rate가 NULL이어도 이미 처리되었으므로, 가격 데이터만 확인
        required_cols = ['upbit_price', 'binance_price', 'bitget_price', 
                        'premium_upbit_binance', 'premium_upbit_bitget', 'premium_binance_bitget']
        df = df.dropna(subset=required_cols)
        
        # Rolling window 적용: 처음 30일 제거 (이동평균 계산을 위해 필요)
        if len(df) > self.rolling_window:
            df = df.iloc[self.rolling_window:].reset_index(drop=True)
        
        return df

    def generate_signals(self, df):
        """최적의 차익거래 기회 선택 (개선된 조건)"""
        df = df.copy()
        df['signal'] = 0
        df['signal_pair'] = None
        df['signal_direction'] = None
        
        for idx, row in df.iterrows():
            z_scores = {}
            
            # upbit_binance 쌍 제외 옵션
            if not self.exclude_upbit_binance:
                z_scores['upbit_binance'] = abs(row['z_score_upbit_binance']) if pd.notna(row['z_score_upbit_binance']) else 0
            else:
                z_scores['upbit_binance'] = 0  # 제외
            
            z_scores['upbit_bitget'] = abs(row['z_score_upbit_bitget']) if pd.notna(row['z_score_upbit_bitget']) else 0
            z_scores['binance_bitget'] = abs(row['z_score_binance_bitget']) if pd.notna(row['z_score_binance_bitget']) else 0
            
            best_pair = max(z_scores, key=z_scores.get)
            best_z = z_scores[best_pair]
            
            # 강화된 진입 조건
            if best_z > self.entry_z:
                if best_pair == 'upbit_binance':
                    z_score = row['z_score_upbit_binance']
                    if z_score > self.entry_z:
                        df.at[idx, 'signal'] = 1
                        df.at[idx, 'signal_pair'] = 'upbit_binance'
                        df.at[idx, 'signal_direction'] = 'short_premium'
                    elif z_score < -self.entry_z:
                        df.at[idx, 'signal'] = -1
                        df.at[idx, 'signal_pair'] = 'upbit_binance'
                        df.at[idx, 'signal_direction'] = 'long_premium'
                        
                elif best_pair == 'upbit_bitget':
                    z_score = row['z_score_upbit_bitget']
                    if z_score > self.entry_z:
                        df.at[idx, 'signal'] = 1
                        df.at[idx, 'signal_pair'] = 'upbit_bitget'
                        df.at[idx, 'signal_direction'] = 'short_premium'
                    elif z_score < -self.entry_z:
                        df.at[idx, 'signal'] = -1
                        df.at[idx, 'signal_pair'] = 'upbit_bitget'
                        df.at[idx, 'signal_direction'] = 'long_premium'
                        
                elif best_pair == 'binance_bitget':
                    z_score = row['z_score_binance_bitget']
                    if z_score > self.entry_z:
                        df.at[idx, 'signal'] = 1
                        df.at[idx, 'signal_pair'] = 'binance_bitget'
                        df.at[idx, 'signal_direction'] = 'short_premium'
                    elif z_score < -self.entry_z:
                        df.at[idx, 'signal'] = -1
                        df.at[idx, 'signal_pair'] = 'binance_bitget'
                        df.at[idx, 'signal_direction'] = 'long_premium'
        
        return df

    def run_backtest(self, df):
        """백테스트 실행"""
        position = 0
        position_pair = None
        capital = self.initial_capital
        history = []
        daily_capital = []
        
        entry_price_high = 0
        entry_price_low = 0
        entry_date = None
        entry_index = None
        
        cost_rate = self.fee_rate + self.slippage
        
        for idx, row in df.iterrows():
            current_date = row['date']
            current_signal = row['signal']
            current_pair = row['signal_pair']
            current_direction = row['signal_direction']
            
            if position == 0:
                if current_signal != 0 and current_pair:
                    position = current_signal
                    position_pair = current_pair
                    entry_date = current_date
                    entry_index = idx
                    
                    if current_pair == 'upbit_binance':
                        if current_direction == 'short_premium':
                            entry_price_high = row['upbit_price']
                            entry_price_low = row['binance_krw']
                        else:
                            entry_price_high = row['binance_krw']
                            entry_price_low = row['upbit_price']
                            
                    elif current_pair == 'upbit_bitget':
                        if current_direction == 'short_premium':
                            entry_price_high = row['upbit_price']
                            entry_price_low = row['bitget_krw']
                        else:
                            entry_price_high = row['bitget_krw']
                            entry_price_low = row['upbit_price']
                            
                    elif current_pair == 'binance_bitget':
                        if current_direction == 'short_premium':
                            entry_price_high = row['binance_krw']
                            entry_price_low = row['bitget_krw']
                        else:
                            entry_price_high = row['bitget_krw']
                            entry_price_low = row['binance_krw']
            
            elif position != 0:
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
                    daily_capital.append({'date': current_date, 'capital': capital})
                    continue
                
                ret_high = (entry_price_high - current_price_high) / entry_price_high if position == 1 else (current_price_high - entry_price_high) / entry_price_high
                ret_low = (current_price_low - entry_price_low) / entry_price_low if position == 1 else (entry_price_low - current_price_low) / entry_price_low
                current_return = (ret_high + ret_low) / 2
                
                should_exit = False
                exit_reason = None
                
                # 조정된 청산 조건 (Z-Score < exit_z, 기본값 0.0)
                if abs(z_score) < abs(self.exit_z):
                    should_exit = True
                    exit_reason = 'z_score_reversion'
                
                elif current_return <= self.stop_loss:
                    should_exit = True
                    exit_reason = 'stop_loss'
                
                elif (current_date - entry_date).days >= self.max_holding_days:
                    should_exit = True
                    exit_reason = 'max_holding_days'
                
                if should_exit:
                    gross_return = current_return
                    net_return = gross_return - (cost_rate * 2)
                    
                    profit = capital * net_return
                    capital += profit
                    
                    history.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'holding_days': (current_date - entry_date).days,
                        'pair': position_pair,
                        'direction': 'Short Premium' if position == 1 else 'Long Premium',
                        'return': net_return,
                        'profit': profit,
                        'capital': capital,
                        'exit_reason': exit_reason
                    })
                    
                    position = 0
                    position_pair = None
                    entry_date = None
                    entry_index = None
            
            daily_capital.append({'date': current_date, 'capital': capital})
        
        return pd.DataFrame(history), pd.DataFrame(daily_capital)

    def calculate_benchmark(self, df):
        """벤치마크 계산"""
        if len(df) < 2:
            return 0.0
        first_price = df['upbit_price'].iloc[0]
        last_price = df['upbit_price'].iloc[-1]
        return (last_price - first_price) / first_price

    def analyze_performance(self, trade_df, daily_capital_df, benchmark_return):
        """성과 분석"""
        if trade_df.empty:
            return {
                "total_trades": 0,
                "final_return": 0.0,
                "annualized_return": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "mdd": 0.0,
                "max_holding_days": 0,
                "avg_holding_days": 0.0,
                "benchmark_return": benchmark_return,
                "excess_return": 0.0
            }
        
        total_trades = len(trade_df)
        final_capital = trade_df['capital'].iloc[-1] if not trade_df.empty else self.initial_capital
        final_return = (final_capital - self.initial_capital) / self.initial_capital
        
        if len(daily_capital_df) > 1:
            days = (daily_capital_df['date'].iloc[-1] - daily_capital_df['date'].iloc[0]).days
            years = days / 365.25
            annualized_return = (1 + final_return) ** (1 / years) - 1 if years > 0 else 0.0
        else:
            annualized_return = 0.0
        
        win_rate = (trade_df['return'] > 0).mean()
        
        daily_capital_df = daily_capital_df.copy()
        daily_capital_df['peak'] = daily_capital_df['capital'].cummax()
        daily_capital_df['drawdown'] = (daily_capital_df['capital'] - daily_capital_df['peak']) / daily_capital_df['peak']
        mdd = daily_capital_df['drawdown'].min()
        
        if len(daily_capital_df) > 1:
            daily_returns = daily_capital_df['capital'].pct_change().dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365.25)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0
        
        max_holding = trade_df['holding_days'].max() if 'holding_days' in trade_df.columns else 0
        avg_holding = trade_df['holding_days'].mean() if 'holding_days' in trade_df.columns else 0.0
        
        excess_return = final_return - benchmark_return
        
        return {
            "total_trades": total_trades,
            "final_return": final_return,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe,
            "win_rate": win_rate,
            "mdd": mdd,
            "max_holding_days": max_holding,
            "avg_holding_days": avg_holding,
            "benchmark_return": benchmark_return,
            "excess_return": excess_return
        }

