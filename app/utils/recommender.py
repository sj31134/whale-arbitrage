"""
최적 전략 추천기
- 특정 날짜 기준 최고 수익률 차익거래 방법 추천
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
elif os.path.exists('/app'):
    # Docker 컨테이너 내부
    ROOT = Path('/app')
else:
    # 로컬 개발 환경
    ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))

from backtest_engine_optimized import OptimizedArbitrageBacktest
from data_loader import DataLoader


class StrategyRecommender:
    def __init__(self):
        self.data_loader = DataLoader()
    
    def recommend_best_strategy(
        self,
        target_date: str,
        coin: str = 'BTC',
        initial_capital: float = 100_000_000
    ) -> Dict:
        """
        최적 전략 추천
        
        Returns:
            {
                "success": bool,
                "data": {
                    "recommended_pair": str,
                    "direction": str,
                    "expected_return": float,
                    "expected_holding_days": int,
                    "current_premium": float,
                    "z_score": float,
                    "execution_steps": List[str],
                    "risks": Dict,
                    "alternatives": List[Dict]
                },
                "error": str (if success=False)
            }
        """
        try:
            # target_date 기준 전후 30일 데이터 로드
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target_dt - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = (target_dt + timedelta(days=30)).strftime("%Y-%m-%d")
            
            # 데이터 로드
            df = self.data_loader.load_exchange_data(start_date, end_date, coin)
            
            if len(df) < 30:
                return {
                    "success": False,
                    "error": f"데이터가 부족합니다. (현재: {len(df)}건)"
                }
            
            # 지표 계산
            backtest = OptimizedArbitrageBacktest(rolling_window=30)
            df = backtest.calculate_indicators(df)
            
            # target_date 행 찾기
            target_df = df[df['date'].dt.date == target_dt.date()]
            
            if target_df.empty:
                # 가장 가까운 날짜 찾기
                if len(df) > 0:
                    df['date_diff'] = (df['date'].dt.date - target_dt.date()).abs()
                    closest_row = df.loc[df['date_diff'].idxmin()]
                    closest_date = closest_row['date'].date()
                    days_diff = abs((closest_date - target_dt.date()).days)
                    
                    return {
                        "success": False,
                        "error": f"{target_date}에 대한 데이터가 없습니다. 가장 가까운 날짜: {closest_date} (차이: {days_diff}일)",
                        "closest_date": closest_date.strftime("%Y-%m-%d")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"{target_date}에 대한 데이터가 없습니다. 해당 기간에 데이터가 존재하지 않습니다."
                    }
            
            row = target_df.iloc[0]
            
            # 각 거래소 쌍별 Z-Score 및 프리미엄 계산 (6개 쌍)
            pairs_data = []
            all_pairs_data = []  # 모든 쌍 (조건 만족 여부와 관계없이)
            
            # 6개 거래소 쌍 정의
            pair_configs = [
                ("업비트-바이낸스", "upbit_binance"),
                ("업비트-비트겟", "upbit_bitget"),
                ("업비트-바이비트", "upbit_bybit"),
                ("바이낸스-비트겟", "binance_bitget"),
                ("바이낸스-바이비트", "binance_bybit"),
                ("비트겟-바이비트", "bitget_bybit")
            ]
            
            for pair_name, pair_code in pair_configs:
                z_col = f'z_score_{pair_code}'
                prem_col = f'premium_{pair_code}'
                
                if z_col in row and pd.notna(row[z_col]):
                    z_score = row[z_col]
                    premium = row[prem_col] if prem_col in row else 0
                    pair_info = {
                        "pair": pair_name,
                        "pair_code": pair_code,
                        "z_score": z_score,
                        "premium": premium,
                        "direction": "short_premium" if z_score > 0 else "long_premium"
                    }
                    all_pairs_data.append(pair_info)
                    if abs(z_score) > 2.5:
                        pairs_data.append(pair_info)
            
            # 진입 조건을 만족하는 쌍이 없으면, 가장 높은 Z-Score를 가진 쌍을 제안
            if not pairs_data:
                if not all_pairs_data:
                    return {
                        "success": False,
                        "error": f"{target_date}에 사용 가능한 거래소 쌍 데이터가 없습니다."
                    }
                
                # Z-Score 절댓값 기준 정렬
                all_pairs_data.sort(key=lambda x: abs(x['z_score']), reverse=True)
                best_pair = all_pairs_data[0]
                
                return {
                    "success": False,
                    "error": f"{target_date}에 진입 조건을 만족하는 거래소 쌍이 없습니다. (Z-Score > 2.5 필요)",
                    "suggestion": {
                        "pair": best_pair['pair'],
                        "pair_code": best_pair['pair_code'],
                        "z_score": best_pair['z_score'],
                        "premium": best_pair['premium'],
                        "direction": best_pair['direction'],
                        "message": f"가장 높은 Z-Score: {best_pair['pair']} (Z-Score={best_pair['z_score']:.2f}, 프리미엄={best_pair['premium']*100:.2f}%)"
                    },
                    "all_pairs": all_pairs_data
                }
            
            # Z-Score 절댓값 기준 정렬
            pairs_data.sort(key=lambda x: abs(x['z_score']), reverse=True)
            
            # 최고 전략 선택
            best = pairs_data[0]
            
            # 시뮬레이션: 실제 청산 시점까지 시뮬레이션
            simulation_result = self._simulate_trade(
                df, target_dt, best['pair_code'], best['direction'], 
                initial_capital, backtest
            )
            
            # 실행 방법 생성
            execution_steps = self._generate_execution_steps(
                best['pair'], best['direction'], coin
            )
            
            # 리스크 정보
            risks = {
                "stop_loss": -0.03,
                "max_holding_days": 30,
                "fee_rate": 0.0005,
                "slippage": 0.0002
            }
            
            # 대안 전략 (2순위, 3순위)
            alternatives = []
            for i, alt in enumerate(pairs_data[1:3], 1):
                alt_sim = self._simulate_trade(
                    df, target_dt, alt['pair_code'], alt['direction'],
                    initial_capital, backtest
                )
                alternatives.append({
                    "rank": i + 1,
                    "pair": alt['pair'],
                    "direction": alt['direction'],
                    "expected_return": alt_sim.get('return', 0),
                    "z_score": alt['z_score'],
                    "premium": alt['premium']
                })
            
            return {
                "success": True,
                "data": {
                    "recommended_pair": best['pair'],
                    "pair_code": best['pair_code'],
                    "direction": best['direction'],
                    "expected_return": simulation_result.get('return', 0),
                    "expected_holding_days": simulation_result.get('holding_days', 0),
                    "current_premium": best['premium'],
                    "z_score": best['z_score'],
                    "execution_steps": execution_steps,
                    "risks": risks,
                    "alternatives": alternatives
                }
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"추천 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
            }
    
    def _simulate_trade(
        self,
        df: pd.DataFrame,
        entry_date: datetime,
        pair_code: str,
        direction: str,
        initial_capital: float,
        backtest: OptimizedArbitrageBacktest
    ) -> Dict:
        """거래 시뮬레이션"""
        # entry_date 이후 데이터만 사용
        entry_df = df[df['date'] >= entry_date].copy()
        
        if len(entry_df) < 2:
            return {"return": 0, "holding_days": 0}
        
        # 진입 가격 - 6개 쌍 지원
        entry_row = entry_df.iloc[0]
        
        # 거래소 쌍별 가격 컬럼 매핑
        pair_prices = {
            'upbit_binance': ('upbit_price', 'binance_krw'),
            'upbit_bitget': ('upbit_price', 'bitget_krw'),
            'upbit_bybit': ('upbit_price', 'bybit_krw'),
            'binance_bitget': ('binance_krw', 'bitget_krw'),
            'binance_bybit': ('binance_krw', 'bybit_krw'),
            'bitget_bybit': ('bitget_krw', 'bybit_krw')
        }
        
        if pair_code not in pair_prices:
            return {"return": 0, "holding_days": 0}
        
        high_col, low_col = pair_prices[pair_code]
        z_score_col = f'z_score_{pair_code}'
        
        if direction == 'short_premium':
            entry_price_high = entry_row[high_col]
            entry_price_low = entry_row[low_col]
        else:
            entry_price_high = entry_row[low_col]
            entry_price_low = entry_row[high_col]
        
        # 청산 조건 확인 (Z-Score < 0.5 또는 최대 보유 기간)
        cost_rate = backtest.fee_rate + backtest.slippage
        
        for idx, row in entry_df.iterrows():
            current_date = row['date']
            z_score = row[z_score_col]
            
            if pd.isna(z_score):
                continue
            
            # 현재 가격 - 6개 쌍 지원
            if pair_code not in pair_prices:
                continue
            
            high_col, low_col = pair_prices[pair_code]
            if direction == 'short_premium':
                current_price_high = row[high_col]
                current_price_low = row[low_col]
            else:
                current_price_high = row[low_col]
                current_price_low = row[high_col]
            
            # 수익률 계산
            ret_high = (entry_price_high - current_price_high) / entry_price_high if direction == 'short_premium' else (current_price_high - entry_price_high) / entry_price_high
            ret_low = (current_price_low - entry_price_low) / entry_price_low if direction == 'short_premium' else (entry_price_low - current_price_low) / entry_price_low
            current_return = (ret_high + ret_low) / 2
            
            # 청산 조건
            holding_days = (current_date - entry_date).days
            
            if abs(z_score) < 0.5 or holding_days >= 30 or current_return <= -0.03:
                net_return = current_return - (cost_rate * 2)
                return {
                    "return": net_return,
                    "holding_days": holding_days
                }
        
        # 최대 보유 기간 도달
        return {
            "return": current_return - (cost_rate * 2),
            "holding_days": 30
        }
    
    def _generate_execution_steps(self, pair: str, direction: str, coin: str) -> List[str]:
        """실행 방법 생성 (6개 쌍 지원)"""
        steps = []
        
        # 거래소 쌍별 실행 방법 매핑
        pair_actions = {
            "업비트-바이낸스": ("업비트", "바이낸스"),
            "업비트-비트겟": ("업비트", "비트겟"),
            "업비트-바이비트": ("업비트", "바이비트"),
            "바이낸스-비트겟": ("바이낸스", "비트겟"),
            "바이낸스-바이비트": ("바이낸스", "바이비트"),
            "비트겟-바이비트": ("비트겟", "바이비트")
        }
        
        if pair in pair_actions:
            ex1, ex2 = pair_actions[pair]
            if direction == "short_premium":
                steps.append(f"1. {ex1}에서 {coin} 매도")
                steps.append(f"2. {ex2}에서 {coin} 매수")
            else:
                steps.append(f"1. {ex1}에서 {coin} 매수")
                steps.append(f"2. {ex2}에서 {coin} 매도")
        
        steps.append("3. 프리미엄 회귀 대기 (Z-Score < 0.5)")
        steps.append("4. 역거래 실행 (청산)")
        
        return steps

