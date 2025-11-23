"""
차익거래 비용 계산기
- OptimizedArbitrageBacktest 활용
- 결과 포맷팅
"""

import sys
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional
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


class CostCalculator:
    def __init__(self):
        pass
    
    def _convert_exchange_names(self, exchanges: List[str]) -> List[str]:
        """한글 거래소 쌍 이름을 영문 코드로 변환"""
        mapping = {
            "업비트-바이낸스": "upbit_binance",
            "업비트-비트겟": "upbit_bitget",
            "바이낸스-비트겟": "binance_bitget"
        }
        return [mapping.get(ex, ex) for ex in exchanges if ex in mapping]
    
    def calculate_arbitrage_cost(
        self,
        from_date: str,
        to_date: str,
        coin: str,
        exchanges: List[str],
        initial_capital: float = 100_000_000,
        fee_rate: float = 0.0005,
        slippage: float = 0.0002,
        entry_z: float = 2.5,
        exit_z: float = 0.5,
        stop_loss: float = -0.03,
        max_holding_days: int = 30
    ) -> Dict:
        """
        차익거래 비용 계산
        
        Returns:
            {
                "success": bool,
                "data": {
                    "total_trades": int,
                    "final_return": float,
                    "total_profit": float,
                    "win_rate": float,
                    "mdd": float,
                    "sharpe_ratio": float,
                    "annualized_return": float,
                    "trades": pd.DataFrame,
                    "daily_capital": pd.DataFrame
                },
                "error": str (if success=False)
            }
        """
        try:
            # 거래소 쌍 변환
            exchange_codes = self._convert_exchange_names(exchanges)
            
            if not exchange_codes:
                return {
                    "success": False,
                    "error": "유효한 거래소 쌍을 선택해주세요."
                }
            
            # 백테스트 엔진 초기화
            backtest = OptimizedArbitrageBacktest(
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage=slippage,
                stop_loss=stop_loss,
                max_holding_days=max_holding_days,
                entry_z=entry_z,
                exit_z=exit_z,
                exclude_upbit_binance="upbit_binance" not in exchange_codes
            )
            
            # 데이터 로드
            df = backtest.load_data(from_date, to_date)
            
            if len(df) < 30:
                return {
                    "success": False,
                    "error": f"데이터가 부족합니다. (현재: {len(df)}건, 최소: 30건 필요)"
                }
            
            # 지표 계산
            df = backtest.calculate_indicators(df)
            
            if len(df) == 0:
                return {
                    "success": False,
                    "error": "지표 계산 후 데이터가 없습니다."
                }
            
            # 벤치마크 계산
            benchmark_return = backtest.calculate_benchmark(df)
            
            # 시그널 생성 (선택된 거래소 쌍만 필터링)
            df = backtest.generate_signals(df)
            
            # 선택된 거래소 쌍만 필터링
            if exchange_codes:
                df = df[df['signal_pair'].isin(exchange_codes) | (df['signal'] == 0)]
            
            # 백테스트 실행
            trades_df, daily_capital_df = backtest.run_backtest(df)
            
            # 성과 분석
            metrics = backtest.analyze_performance(trades_df, daily_capital_df, benchmark_return)
            
            return {
                "success": True,
                "data": {
                    **metrics,
                    "trades": trades_df,
                    "daily_capital": daily_capital_df,
                    "benchmark_return": benchmark_return
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"계산 중 오류 발생: {str(e)}"
            }

