"""
Project 2: 최적화된 차익거래 백테스트 엔진
- 4개 거래소 지원 (업비트, 바이낸스, 비트겟, 바이비트)
- 6개 거래소 쌍 차익거래
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
        
        # DataLoader를 사용하여 Supabase 지원
        try:
            import sys
            sys.path.insert(0, str(ROOT / "app" / "utils"))
            from data_loader import DataLoader
            self.data_loader = DataLoader()
            self.use_data_loader = True
        except Exception as e:
            import logging
            logging.warning(f"DataLoader 초기화 실패, SQLite 직접 사용: {e}")
            self.data_loader = None
            self.use_data_loader = False
            self.conn = sqlite3.connect(DB_PATH)

    def load_data(self, start_date, end_date):
        """4개 거래소 데이터 로드 및 병합"""
        # DataLoader를 사용하는 경우 (Supabase 지원)
        if self.use_data_loader and self.data_loader:
            try:
                df = self.data_loader.load_exchange_data(start_date, end_date, 'BTC')
                if not df.empty:
                    return df
            except Exception as e:
                import logging
                logging.warning(f"DataLoader를 통한 데이터 로드 실패, SQLite 직접 사용: {e}")
                # SQLite로 폴백
        
        # SQLite 직접 사용 (로컬 환경 또는 DataLoader 실패 시)
        if not hasattr(self, 'conn') or self.conn is None:
            self.conn = sqlite3.connect(DB_PATH)
        
        query = f"""
        SELECT 
            u.date,
            u.trade_price as upbit_price,
            b.close as binance_price,
            bg.close as bitget_price,
            bb.close as bybit_price,
            e.krw_usd
        FROM upbit_daily u
        LEFT JOIN binance_spot_daily b ON u.date = b.date AND b.symbol = 'BTCUSDT'
        LEFT JOIN bitget_spot_daily bg ON u.date = bg.date AND bg.symbol = 'BTCUSDT'
        LEFT JOIN bybit_spot_daily bb ON u.date = bb.date AND bb.symbol = 'BTCUSDT'
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
        df['bybit_krw'] = df['bybit_price'] * df['krw_usd']
        
        return df

    def calculate_indicators(self, df):
        """각 거래소 쌍별 프리미엄 및 Z-Score 계산 (6개 쌍)"""
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
        
        # 3. 업비트 vs 바이비트 프리미엄
        df['premium_upbit_bybit'] = (df['upbit_price'] - df['bybit_krw']) / df['bybit_krw']
        df['premium_upbit_bybit_mean'] = df['premium_upbit_bybit'].rolling(window=self.rolling_window).mean()
        df['premium_upbit_bybit_std'] = df['premium_upbit_bybit'].rolling(window=self.rolling_window).std()
        df['z_score_upbit_bybit'] = (
            (df['premium_upbit_bybit'] - df['premium_upbit_bybit_mean']) 
            / df['premium_upbit_bybit_std']
        )
        
        # 4. 바이낸스 vs 비트겟 프리미엄
        df['premium_binance_bitget'] = (df['binance_krw'] - df['bitget_krw']) / df['bitget_krw']
        df['premium_binance_bitget_mean'] = df['premium_binance_bitget'].rolling(window=self.rolling_window).mean()
        df['premium_binance_bitget_std'] = df['premium_binance_bitget'].rolling(window=self.rolling_window).std()
        df['z_score_binance_bitget'] = (
            (df['premium_binance_bitget'] - df['premium_binance_bitget_mean']) 
            / df['premium_binance_bitget_std']
        )
        
        # 5. 바이낸스 vs 바이비트 프리미엄
        df['premium_binance_bybit'] = (df['binance_krw'] - df['bybit_krw']) / df['bybit_krw']
        df['premium_binance_bybit_mean'] = df['premium_binance_bybit'].rolling(window=self.rolling_window).mean()
        df['premium_binance_bybit_std'] = df['premium_binance_bybit'].rolling(window=self.rolling_window).std()
        df['z_score_binance_bybit'] = (
            (df['premium_binance_bybit'] - df['premium_binance_bybit_mean']) 
            / df['premium_binance_bybit_std']
        )
        
        # 6. 비트겟 vs 바이비트 프리미엄
        df['premium_bitget_bybit'] = (df['bitget_krw'] - df['bybit_krw']) / df['bybit_krw']
        df['premium_bitget_bybit_mean'] = df['premium_bitget_bybit'].rolling(window=self.rolling_window).mean()
        df['premium_bitget_bybit_std'] = df['premium_bitget_bybit'].rolling(window=self.rolling_window).std()
        df['z_score_bitget_bybit'] = (
            (df['premium_bitget_bybit'] - df['premium_bitget_bybit_mean']) 
            / df['premium_bitget_bybit_std']
        )
        
        # NULL 값 처리: 핵심 가격 데이터만 확인
        required_cols = ['upbit_price', 'binance_price', 'bitget_price', 'bybit_price']
        df = df.dropna(subset=required_cols)
        
        # Rolling window 적용: 처음 30일 제거 (이동평균 계산을 위해 필요)
        if len(df) > self.rolling_window:
            df = df.iloc[self.rolling_window:].reset_index(drop=True)
        
        return df

    def generate_signals(self, df):
        """최적의 차익거래 기회 선택 (6개 거래소 쌍)"""
        df = df.copy()
        df['signal'] = 0
        df['signal_pair'] = None
        df['signal_direction'] = None
        
        # 6개 거래소 쌍 정의
        all_pairs = [
            'upbit_binance', 'upbit_bitget', 'upbit_bybit',
            'binance_bitget', 'binance_bybit', 'bitget_bybit'
        ]
        
        for idx, row in df.iterrows():
            z_scores = {}
            
            for pair in all_pairs:
                z_col = f'z_score_{pair}'
                if z_col in row and pd.notna(row[z_col]):
                    # upbit_binance 쌍 제외 옵션
                    if pair == 'upbit_binance' and self.exclude_upbit_binance:
                        z_scores[pair] = 0
                    else:
                        z_scores[pair] = abs(row[z_col])
                else:
                    z_scores[pair] = 0
            
            best_pair = max(z_scores, key=z_scores.get)
            best_z = z_scores[best_pair]
            
            # 강화된 진입 조건
            if best_z > self.entry_z:
                z_col = f'z_score_{best_pair}'
                z_score = row[z_col]
                
                if z_score > self.entry_z:
                    df.at[idx, 'signal'] = 1
                    df.at[idx, 'signal_pair'] = best_pair
                    df.at[idx, 'signal_direction'] = 'short_premium'
                elif z_score < -self.entry_z:
                    df.at[idx, 'signal'] = -1
                    df.at[idx, 'signal_pair'] = best_pair
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
                    
                    # 거래소 쌍별 가격 매핑
                    pair_prices = {
                        'upbit_binance': ('upbit_price', 'binance_krw'),
                        'upbit_bitget': ('upbit_price', 'bitget_krw'),
                        'upbit_bybit': ('upbit_price', 'bybit_krw'),
                        'binance_bitget': ('binance_krw', 'bitget_krw'),
                        'binance_bybit': ('binance_krw', 'bybit_krw'),
                        'bitget_bybit': ('bitget_krw', 'bybit_krw')
                    }
                    
                    if current_pair in pair_prices:
                        high_col, low_col = pair_prices[current_pair]
                        if current_direction == 'short_premium':
                            entry_price_high = row[high_col]
                            entry_price_low = row[low_col]
                        else:
                            entry_price_high = row[low_col]
                            entry_price_low = row[high_col]
            
            elif position != 0:
                # 거래소 쌍별 가격 매핑
                pair_prices = {
                    'upbit_binance': ('upbit_price', 'binance_krw'),
                    'upbit_bitget': ('upbit_price', 'bitget_krw'),
                    'upbit_bybit': ('upbit_price', 'bybit_krw'),
                    'binance_bitget': ('binance_krw', 'bitget_krw'),
                    'binance_bybit': ('binance_krw', 'bybit_krw'),
                    'bitget_bybit': ('bitget_krw', 'bybit_krw')
                }
                
                if position_pair not in pair_prices:
                    daily_capital.append({'date': current_date, 'capital': capital})
                    continue
                
                high_col, low_col = pair_prices[position_pair]
                current_price_high = row[high_col] if position == 1 else row[low_col]
                current_price_low = row[low_col] if position == 1 else row[high_col]
                z_score = row[f'z_score_{position_pair}']
                
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

