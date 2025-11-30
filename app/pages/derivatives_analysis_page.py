"""
파생상품 지표 분석 페이지
- OI (미결제약정) 분석
- 롱/숏 비율 분석
- Taker 매수/매도 압력 분석
- 펀딩비 분석
"""

import streamlit as st
from datetime import datetime, date, timedelta
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    ROOT = Path('/mount/src/whale-arbitrage')
elif os.path.exists('/app'):
    ROOT = Path('/app')
else:
    ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

from data_loader import DataLoader


def render():
    st.header("📊 파생상품 지표 분석")
    st.markdown("미결제약정(OI), 롱/숏 비율, Taker 압력, 펀딩비 등 파생상품 시장 지표를 종합 분석합니다.")
    
    # 데이터 로더 초기화
    try:
        data_loader = DataLoader()
    except Exception as e:
        st.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 분석 설정")
    
    # 코인 선택
    coin = st.sidebar.selectbox(
        "코인",
        ["BTC", "ETH"],
        index=0
    )
    
    # 날짜 범위 선택
    st.sidebar.subheader("📅 날짜 범위")
    end_date = st.sidebar.date_input(
        "종료 날짜",
        value=date.today(),
        min_value=date(2022, 1, 1),
        max_value=date.today()
    )
    
    days_back = st.sidebar.slider(
        "분석 기간 (일)",
        min_value=7,
        max_value=90,
        value=30,
        step=7
    )
    
    start_date = end_date - timedelta(days=days_back)
    
    # 분석 실행
    if st.sidebar.button("🔍 분석 실행", type="primary"):
        with st.spinner("데이터 로딩 중..."):
            symbol = f"{coin}USDT"
            
            # 데이터 로드
            metrics_df = data_loader.load_futures_extended_metrics(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                symbol
            )
            
            oi_df = data_loader.load_risk_data(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                coin
            )
            
            if metrics_df.empty and oi_df.empty:
                st.error("❌ 데이터를 불러올 수 없습니다.")
                if coin == 'ETH':
                    st.info("💡 ETH 데이터는 2022-01-01부터 수집되었지만, 선택한 기간에 데이터가 없을 수 있습니다.")
                    st.info("💡 분석 기간을 조정하거나, BTC로 변경해보세요.")
                st.stop()
            
            # 1. OI (미결제약정) 분석
            st.subheader("📈 미결제약정 (OI) 분석")
            
            # OI 데이터 유효성 확인
            if 'sum_open_interest' in oi_df.columns and len(oi_df) > 0:
                # 0이 아닌 OI 데이터 확인
                oi_valid = oi_df[oi_df['sum_open_interest'].notna() & (oi_df['sum_open_interest'] != 0)]
                if len(oi_valid) == 0:
                    st.warning(f"⚠️ {coin} OI 데이터가 없거나 모두 0입니다.")
                    if coin == 'ETH':
                        st.info(f"💡 ETH OI 데이터는 2022-01-01부터 수집되었지만, 선택한 기간({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})에 데이터가 없습니다.")
                        st.info("💡 분석 기간을 조정하거나, BTC로 변경해보세요.")
                    st.stop()
                col1, col2 = st.columns(2)
                
                with col1:
                    # OI 추이
                    fig_oi = px.line(
                        oi_df,
                        x='date',
                        y='sum_open_interest',
                        title=f'{coin} OI 추이',
                        labels={'sum_open_interest': 'OI', 'date': '날짜'}
                    )
                    fig_oi.update_traces(line_color='#1f77b4', line_width=2)
                    st.plotly_chart(fig_oi, use_container_width=True)
                
                with col2:
                    # OI 변화율
                    oi_df['oi_change_pct'] = oi_df['sum_open_interest'].pct_change() * 100
                    fig_oi_change = px.bar(
                        oi_df,
                        x='date',
                        y='oi_change_pct',
                        title='OI 일일 변화율 (%)',
                        labels={'oi_change_pct': '변화율 (%)', 'date': '날짜'},
                        color='oi_change_pct',
                        color_continuous_scale=['red', 'white', 'green']
                    )
                    fig_oi_change.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig_oi_change, use_container_width=True)
                
                # OI 통계
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("현재 OI", f"{oi_df['sum_open_interest'].iloc[-1]:,.0f}")
                with col2:
                    st.metric("평균 OI", f"{oi_df['sum_open_interest'].mean():,.0f}")
                with col3:
                    st.metric("최대 OI", f"{oi_df['sum_open_interest'].max():,.0f}")
                with col4:
                    oi_change = ((oi_df['sum_open_interest'].iloc[-1] - oi_df['sum_open_interest'].iloc[0]) / 
                                oi_df['sum_open_interest'].iloc[0] * 100)
                    st.metric("기간 변화", f"{oi_change:+.1f}%")
            else:
                st.info("💡 OI 데이터가 없습니다.")
            
            st.markdown("---")
            
            # 2. 롱/숏 비율 분석
            st.subheader("⚖️ 롱/숏 비율 분석")
            
            if 'top_trader_long_short_ratio' in metrics_df.columns and len(metrics_df) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Top Trader 롱/숏 비율
                    fig_ls = px.line(
                        metrics_df,
                        x='date',
                        y='top_trader_long_short_ratio',
                        title='Top Trader 롱/숏 비율',
                        labels={'top_trader_long_short_ratio': '비율', 'date': '날짜'}
                    )
                    fig_ls.add_hline(y=1.0, line_dash="dash", line_color="gray",
                                    annotation_text="1.0 (균형)")
                    fig_ls.update_traces(line_color='#ff7f0e', line_width=2)
                    st.plotly_chart(fig_ls, use_container_width=True)
                
                with col2:
                    # 롱/숏 계정 비율
                    if 'long_account_pct' in metrics_df.columns and 'short_account_pct' in metrics_df.columns:
                        fig_account = go.Figure()
                        fig_account.add_trace(go.Scatter(
                            x=metrics_df['date'],
                            y=metrics_df['long_account_pct'] * 100,
                            mode='lines',
                            name='롱 계정 비율',
                            fill='tonexty',
                            line=dict(color='green')
                        ))
                        fig_account.add_trace(go.Scatter(
                            x=metrics_df['date'],
                            y=metrics_df['short_account_pct'] * 100,
                            mode='lines',
                            name='숏 계정 비율',
                            fill='tozeroy',
                            line=dict(color='red')
                        ))
                        fig_account.update_layout(
                            title='롱/숏 계정 비율',
                            xaxis_title='날짜',
                            yaxis_title='비율 (%)',
                            height=400
                        )
                        st.plotly_chart(fig_account, use_container_width=True)
                    else:
                        st.info("계정 비율 데이터 없음")
                
                # 롱/숏 통계
                col1, col2, col3 = st.columns(3)
                with col1:
                    latest_ls = metrics_df['top_trader_long_short_ratio'].iloc[-1]
                    st.metric("현재 롱/숏 비율", f"{latest_ls:.3f}",
                             "롱 우세" if latest_ls > 1.0 else "숏 우세")
                with col2:
                    avg_ls = metrics_df['top_trader_long_short_ratio'].mean()
                    st.metric("평균 롱/숏 비율", f"{avg_ls:.3f}")
                with col3:
                    ls_change = metrics_df['top_trader_long_short_ratio'].iloc[-1] - metrics_df['top_trader_long_short_ratio'].iloc[0]
                    st.metric("기간 변화", f"{ls_change:+.3f}")
            else:
                st.info("💡 롱/숏 비율 데이터가 없습니다.")
            
            st.markdown("---")
            
            # 3. Taker 매수/매도 압력 분석
            st.subheader("💹 Taker 매수/매도 압력 분석")
            
            if 'taker_buy_sell_ratio' in metrics_df.columns and len(metrics_df) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Taker 비율 추이 (nan 값 제거)
                    taker_clean_df = metrics_df[['date', 'taker_buy_sell_ratio']].dropna()
                    if len(taker_clean_df) > 0:
                        fig_taker = px.line(
                            taker_clean_df,
                            x='date',
                            y='taker_buy_sell_ratio',
                            title='Taker 매수/매도 비율',
                            labels={'taker_buy_sell_ratio': '비율', 'date': '날짜'}
                        )
                        fig_taker.add_hline(y=1.0, line_dash="dash", line_color="gray",
                                           annotation_text="1.0 (균형)")
                        fig_taker.update_traces(line_color='#2ca02c', line_width=2)
                        st.plotly_chart(fig_taker, use_container_width=True)
                    else:
                        st.info("Taker 비율 데이터 없음")
                
                with col2:
                    # Taker 거래량
                    if 'taker_buy_vol' in metrics_df.columns and 'taker_sell_vol' in metrics_df.columns:
                        fig_vol = go.Figure()
                        fig_vol.add_trace(go.Bar(
                            x=metrics_df['date'],
                            y=metrics_df['taker_buy_vol'],
                            name='매수 거래량',
                            marker_color='green'
                        ))
                        fig_vol.add_trace(go.Bar(
                            x=metrics_df['date'],
                            y=metrics_df['taker_sell_vol'],
                            name='매도 거래량',
                            marker_color='red'
                        ))
                        fig_vol.update_layout(
                            title='Taker 매수/매도 거래량',
                            xaxis_title='날짜',
                            yaxis_title='거래량',
                            barmode='group',
                            height=400
                        )
                        st.plotly_chart(fig_vol, use_container_width=True)
                    else:
                        st.info("거래량 데이터 없음")
                
                # Taker 통계
                col1, col2, col3 = st.columns(3)
                with col1:
                    # nan 값 처리
                    latest_taker = metrics_df['taker_buy_sell_ratio'].dropna()
                    if len(latest_taker) > 0:
                        latest_taker_val = latest_taker.iloc[-1]
                        if pd.notna(latest_taker_val):
                            if latest_taker_val > 1.1:
                                status = "🔴 강한 매수"
                            elif latest_taker_val > 1.0:
                                status = "🟡 약한 매수"
                            elif latest_taker_val > 0.9:
                                status = "🟡 약한 매도"
                            else:
                                status = "🔴 강한 매도"
                            st.metric("현재 Taker 비율", f"{latest_taker_val:.3f}", status)
                        else:
                            st.metric("현재 Taker 비율", "N/A", "데이터 없음")
                    else:
                        st.metric("현재 Taker 비율", "N/A", "데이터 없음")
                with col2:
                    avg_taker = metrics_df['taker_buy_sell_ratio'].dropna().mean()
                    if pd.notna(avg_taker):
                        st.metric("평균 Taker 비율", f"{avg_taker:.3f}")
                    else:
                        st.metric("평균 Taker 비율", "N/A")
                with col3:
                    taker_clean = metrics_df['taker_buy_sell_ratio'].dropna()
                    if len(taker_clean) > 1:
                        taker_change = taker_clean.iloc[-1] - taker_clean.iloc[0]
                        st.metric("기간 변화", f"{taker_change:+.3f}")
                    else:
                        st.metric("기간 변화", "N/A")
            else:
                st.info("💡 Taker 비율 데이터가 없습니다.")
            
            st.markdown("---")
            
            # 4. 펀딩비 분석
            st.subheader("💰 펀딩비 분석")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Binance 펀딩비
                if 'avg_funding_rate' in oi_df.columns and len(oi_df) > 0:
                    # 유효한 펀딩비 데이터 확인
                    funding_valid = oi_df[oi_df['avg_funding_rate'].notna()]
                    if len(funding_valid) > 0:
                        fig_funding = px.line(
                            funding_valid,
                            x='date',
                            y=funding_valid['avg_funding_rate'] * 100,
                            title='Binance 펀딩비 (%)',
                            labels={'avg_funding_rate': '펀딩비 (%)', 'date': '날짜'}
                        )
                        fig_funding.add_hline(y=0, line_dash="dash", line_color="gray")
                        fig_funding.update_traces(line_color='#d62728', line_width=2)
                        st.plotly_chart(fig_funding, use_container_width=True)
                    else:
                        st.warning(f"⚠️ {coin} Binance 펀딩비 데이터가 없습니다.")
                        if coin == 'ETH':
                            st.info("💡 ETH 펀딩비 데이터는 2022-01-01부터 수집되었지만, 선택한 기간에 데이터가 없을 수 있습니다.")
                else:
                    st.warning(f"⚠️ {coin} Binance 펀딩비 데이터가 없습니다.")
                    if coin == 'ETH':
                        st.info("💡 ETH 펀딩비 데이터는 2022-01-01부터 수집되었지만, 선택한 기간에 데이터가 없을 수 있습니다.")
            
            with col2:
                # Bybit 펀딩비
                if 'bybit_funding_rate' in metrics_df.columns and len(metrics_df) > 0:
                    fig_bybit = px.line(
                        metrics_df,
                        x='date',
                        y=metrics_df['bybit_funding_rate'] * 100,
                        title='Bybit 펀딩비 (%)',
                        labels={'bybit_funding_rate': '펀딩비 (%)', 'date': '날짜'}
                    )
                    fig_bybit.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig_bybit.update_traces(line_color='#9467bd', line_width=2)
                    st.plotly_chart(fig_bybit, use_container_width=True)
                else:
                    st.info("Bybit 펀딩비 데이터 없음")
            
            # 펀딩비 통계
            if 'avg_funding_rate' in oi_df.columns and len(oi_df) > 0:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    latest_funding = oi_df['avg_funding_rate'].iloc[-1] * 100
                    st.metric("현재 펀딩비", f"{latest_funding:.4f}%",
                             "롱 지불" if latest_funding > 0 else "숏 지불")
                with col2:
                    avg_funding = oi_df['avg_funding_rate'].mean() * 100
                    st.metric("평균 펀딩비", f"{avg_funding:.4f}%")
                with col3:
                    max_funding = oi_df['avg_funding_rate'].max() * 100
                    st.metric("최대 펀딩비", f"{max_funding:.4f}%")
                with col4:
                    min_funding = oi_df['avg_funding_rate'].min() * 100
                    st.metric("최소 펀딩비", f"{min_funding:.4f}%")
            
            st.markdown("---")
            
            # 5. 종합 분석
            st.subheader("📊 종합 분석")
            
            # 상관관계 분석
            if len(metrics_df) > 0 and len(oi_df) > 0:
                # 데이터 병합
                merged_df = pd.merge(
                    oi_df[['date', 'sum_open_interest', 'avg_funding_rate', 'volatility_24h']],
                    metrics_df[['date', 'top_trader_long_short_ratio', 'taker_buy_sell_ratio']],
                    on='date',
                    how='inner'
                )
                
                if len(merged_df) > 0:
                    # 상관관계 히트맵
                    corr_cols = ['sum_open_interest', 'avg_funding_rate', 'volatility_24h',
                                'top_trader_long_short_ratio', 'taker_buy_sell_ratio']
                    corr_df = merged_df[corr_cols].corr()
                    
                    fig_corr = px.imshow(
                        corr_df,
                        title='파생상품 지표 상관관계',
                        color_continuous_scale='RdBu',
                        aspect='auto'
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
    
    else:
        st.info("👈 사이드바에서 설정을 선택한 후 '분석 실행' 버튼을 클릭하세요.")

