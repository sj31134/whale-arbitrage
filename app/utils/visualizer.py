"""
시각화 유틸리티
- Plotly 차트 생성
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional


class Visualizer:
    @staticmethod
    def plot_return_curve(daily_capital_df: pd.DataFrame, initial_capital: float = 100_000_000):
        """수익률 곡선 차트"""
        df = daily_capital_df.copy()
        df['return_pct'] = ((df['capital'] - initial_capital) / initial_capital) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['return_pct'],
            mode='lines',
            name='수익률',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="0%")
        
        fig.update_layout(
            title="수익률 곡선",
            xaxis_title="날짜",
            yaxis_title="수익률 (%)",
            hovermode='x unified',
            height=400
        )
        
        return fig
    
    @staticmethod
    def plot_drawdown(daily_capital_df: pd.DataFrame):
        """낙폭 (Drawdown) 차트"""
        df = daily_capital_df.copy()
        df['peak'] = df['capital'].cummax()
        df['drawdown'] = ((df['capital'] - df['peak']) / df['peak']) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['drawdown'],
            mode='lines',
            name='낙폭',
            line=dict(color='#d62728', width=2),
            fill='tozeroy',
            fillcolor='rgba(214, 39, 40, 0.2)'
        ))
        
        fig.update_layout(
            title="낙폭 (Drawdown)",
            xaxis_title="날짜",
            yaxis_title="낙폭 (%)",
            hovermode='x unified',
            height=300
        )
        
        return fig
    
    @staticmethod
    def plot_premium_timeline(df: pd.DataFrame, pair: str, target_date: Optional[str] = None):
        """프리미엄 타임라인 차트"""
        fig = go.Figure()
        
        if pair == "업비트-바이낸스":
            premium_col = 'premium_upbit_binance'
            z_score_col = 'z_score_upbit_binance'
        elif pair == "업비트-비트겟":
            premium_col = 'premium_upbit_bitget'
            z_score_col = 'z_score_upbit_bitget'
        elif pair == "바이낸스-비트겟":
            premium_col = 'premium_binance_bitget'
            z_score_col = 'z_score_binance_bitget'
        else:
            return None
        
        # 프리미엄 차트
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df[premium_col] * 100,
            mode='lines',
            name='프리미엄 (%)',
            line=dict(color='#2ca02c', width=2),
            yaxis='y'
        ))
        
        # Z-Score 차트 (보조 축)
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df[z_score_col],
            mode='lines',
            name='Z-Score',
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            yaxis='y2'
        ))
        
        # 진입/청산 기준선
        fig.add_hline(y=2.5, line_dash="dot", line_color="blue", annotation_text="진입 (2.5)", yref='y2')
        fig.add_hline(y=0.5, line_dash="dot", line_color="red", annotation_text="청산 (0.5)", yref='y2')
        fig.add_hline(y=-2.5, line_dash="dot", line_color="blue", annotation_text="진입 (-2.5)", yref='y2')
        fig.add_hline(y=-0.5, line_dash="dot", line_color="red", annotation_text="청산 (-0.5)", yref='y2')
        
        # 타겟 날짜 표시
        if target_date:
            fig.add_vline(
                x=target_date,
                line_dash="dash",
                line_color="purple",
                annotation_text="선택 날짜"
            )
        
        fig.update_layout(
            title=f"{pair} 프리미엄 및 Z-Score 타임라인",
            xaxis_title="날짜",
            yaxis=dict(title="프리미엄 (%)", side="left"),
            yaxis2=dict(title="Z-Score", side="right", overlaying="y"),
            hovermode='x unified',
            height=400
        )
        
        return fig

