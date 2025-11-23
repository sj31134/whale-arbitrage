"""
기능 1: 차익거래 비용 계산기 페이지
"""

import streamlit as st
from datetime import datetime, date
import sys
from pathlib import Path
import pandas as pd
import os

# Docker 컨테이너 내부에서는 /app이 루트
if os.path.exists('/app'):
    ROOT = Path('/app')
else:
    ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

from data_loader import DataLoader
from calculator import CostCalculator
from visualizer import Visualizer


def render():
    st.header("📊 차익거래 비용 계산기")
    st.markdown("특정 기간, 코인, 거래소 조합에 대한 차익거래 비용 및 수익률을 계산합니다.")
    
    # 데이터 로더 초기화
    data_loader = DataLoader()
    calculator = CostCalculator()
    
    # 사용 가능한 날짜 범위 조회
    min_date, max_date = data_loader.get_available_dates('BTC')
    
    if min_date and max_date:
        st.info(f"📅 사용 가능한 데이터 기간: {min_date} ~ {max_date}")
        min_date_obj = datetime.strptime(min_date, "%Y-%m-%d").date()
        max_date_obj = datetime.strptime(max_date, "%Y-%m-%d").date()
    else:
        min_date_obj = date(2024, 1, 1)
        max_date_obj = date.today()
    
    # 입력 섹션
    st.sidebar.header("📋 입력 파라미터")
    
    # 날짜 선택
    st.sidebar.subheader("📅 기간 설정")
    from_date = st.sidebar.date_input(
        "시작 날짜 (From)",
        value=min_date_obj,
        min_value=min_date_obj,
        max_value=max_date_obj
    )
    
    to_date = st.sidebar.date_input(
        "종료 날짜 (To)",
        value=max_date_obj,
        min_value=min_date_obj,
        max_value=max_date_obj
    )
        
    # 코인 선택
    st.sidebar.subheader("🪙 코인 및 거래소")
    coin = st.sidebar.selectbox("코인", ["BTC", "ETH"], index=0)
    
    # 거래소 쌍 선택
    exchange_options = ["업비트-바이낸스", "업비트-비트겟", "바이낸스-비트겟"]
    exchanges = st.sidebar.multiselect(
        "거래소 쌍",
        exchange_options,
        default=["바이낸스-비트겟", "업비트-비트겟"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 자본 설정")
    initial_capital = st.sidebar.number_input(
        "초기 자본 (KRW)",
        min_value=1_000_000,
        max_value=1_000_000_000_000,
        value=100_000_000,
        step=10_000_000,
        format="%d"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ 거래 설정")
    fee_rate = st.sidebar.number_input(
        "수수료율 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.05,
        step=0.01,
        format="%.2f"
    ) / 100
    
    slippage = st.sidebar.number_input(
        "슬리피지 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.02,
        step=0.01,
        format="%.2f"
    ) / 100
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 전략 파라미터")
    entry_z = st.sidebar.number_input(
        "진입 조건 (Z-Score)",
        min_value=1.0,
        max_value=5.0,
        value=2.5,
        step=0.1,
        format="%.1f"
    )
    
    exit_z = st.sidebar.number_input(
        "청산 조건 (Z-Score)",
        min_value=0.0,
        max_value=2.0,
        value=0.5,
        step=0.1,
        format="%.1f"
    )
    
    stop_loss = st.sidebar.number_input(
        "손절매 (%)",
        min_value=-10.0,
        max_value=0.0,
        value=-3.0,
        step=0.5,
        format="%.1f"
    ) / 100
    
    max_holding_days = st.sidebar.number_input(
        "최대 보유 기간 (일)",
        min_value=1,
        max_value=90,
        value=30,
        step=1
    )
    
    # 계산 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calculate_button = st.button("🚀 계산하기", type="primary", use_container_width=True)
    
    if calculate_button:
        # 입력 검증
        if not exchanges:
            st.error("⚠️ 최소 1개 이상의 거래소 쌍을 선택해주세요.")
            return
        
        if from_date > to_date:
            st.error("⚠️ 시작 날짜가 종료 날짜보다 늦습니다.")
            return
        
        # 날짜 범위 검증
        is_valid, error_msg = data_loader.validate_date_range(
            from_date.strftime("%Y-%m-%d"),
            to_date.strftime("%Y-%m-%d"),
            coin
        )
        
        if not is_valid:
            st.error(f"⚠️ {error_msg}")
            return
        
        # 계산 실행
        with st.spinner("계산 중... 잠시만 기다려주세요."):
            result = calculator.calculate_arbitrage_cost(
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
                coin=coin,
                exchanges=exchanges,
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage=slippage,
                entry_z=entry_z,
                exit_z=exit_z,
                stop_loss=stop_loss,
                max_holding_days=max_holding_days
            )
        
        if not result["success"]:
            st.error(f"❌ {result['error']}")
            return
        
        data = result["data"]
        
        # 결과 표시
        st.success("✅ 계산 완료!")
        st.markdown("---")
        
        # 주요 지표 (카드)
        st.subheader("📊 주요 지표")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "최종 수익률",
                f"{data['final_return'] * 100:.2f}%",
                delta=f"{data['excess_return'] * 100:.2f}%p (vs 벤치마크)"
            )
        
        with col2:
            st.metric(
                "총 거래 횟수",
                f"{data['total_trades']}회",
                delta=f"승률 {data['win_rate'] * 100:.1f}%"
            )
        
        with col3:
            st.metric(
                "Sharpe Ratio",
                f"{data['sharpe_ratio']:.2f}",
                delta=f"MDD {data['mdd'] * 100:.2f}%"
            )
        
        with col4:
            st.metric(
                "연율화 수익률",
                f"{data['annualized_return'] * 100:.2f}%",
                delta=f"벤치마크 {data['benchmark_return'] * 100:.2f}%"
            )
        
        # 수익금
        total_profit = data['daily_capital']['capital'].iloc[-1] - initial_capital
        st.info(f"💰 총 수익금: {total_profit:,.0f} KRW")
        
        st.markdown("---")
        
        # 차트
        st.subheader("📈 수익률 곡선")
        fig_return = Visualizer.plot_return_curve(data['daily_capital'], initial_capital)
        st.plotly_chart(fig_return, use_container_width=True)
        
        st.subheader("📉 낙폭 (Drawdown)")
        fig_dd = Visualizer.plot_drawdown(data['daily_capital'])
        st.plotly_chart(fig_dd, use_container_width=True)
        
        # 거래 내역
        if not data['trades'].empty:
            st.markdown("---")
            st.subheader("📋 거래 내역")
            
            # 거래소 쌍별 통계
            st.markdown("#### 거래소 쌍별 통계")
            pair_stats = data['trades'].groupby('pair').agg({
                'return': ['count', 'mean', lambda x: (x > 0).mean()],
                'profit': 'sum',
                'holding_days': 'mean'
            })
            st.dataframe(pair_stats, use_container_width=True)
            
            # 거래 내역 테이블
            st.markdown("#### 상세 거래 내역")
            trades_display = data['trades'].copy()
            trades_display['return'] = (trades_display['return'] * 100).round(2)
            trades_display['profit'] = trades_display['profit'].round(0)
            trades_display = trades_display.rename(columns={
                'return': '수익률 (%)',
                'profit': '수익금 (KRW)',
                'holding_days': '보유 기간 (일)',
                'pair': '거래소 쌍',
                'direction': '방향',
                'exit_reason': '청산 사유'
            })
            st.dataframe(trades_display, use_container_width=True)
    
    # 데이터 로더 연결 종료
    data_loader.close()

