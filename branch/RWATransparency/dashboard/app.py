"""
RWA Transparency Dashboard

Streamlit 기반 RWA 리스크 모니터링 대시보드.
거래소/VC용 실시간 투명성 스코어카드.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# 페이지 설정
st.set_page_config(
    page_title="RWA Transparency Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
    }
    .high-score { color: #4CAF50; font-weight: bold; }
    .medium-score { color: #FFC107; font-weight: bold; }
    .low-score { color: #F44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """데이터 로드"""
    base_path = os.path.dirname(__file__)
    
    # TDT 점수
    tdt_path = os.path.join(base_path, '../data/processed/tdt_scores.csv')
    if os.path.exists(tdt_path):
        df_tdt = pd.read_csv(tdt_path)
    else:
        df_tdt = pd.DataFrame()
    
    # 패널 데이터
    panel_path = os.path.join(base_path, '../data/processed/final_panel_data.csv')
    if os.path.exists(panel_path):
        df_panel = pd.read_csv(panel_path)
    else:
        df_panel = pd.DataFrame()
    
    # 공시 데이터
    disclosure_path = os.path.join(base_path, '../data/raw/offchain_disclosure.csv')
    if os.path.exists(disclosure_path):
        df_disclosure = pd.read_csv(disclosure_path)
    else:
        df_disclosure = pd.DataFrame()
    
    return df_tdt, df_panel, df_disclosure

def get_score_color(score):
    """점수에 따른 색상 반환"""
    if score >= 70:
        return "green"
    elif score >= 40:
        return "orange"
    else:
        return "red"

def get_score_label(score):
    """점수에 따른 등급 반환"""
    if score >= 70:
        return "🟢 High"
    elif score >= 40:
        return "🟡 Medium"
    else:
        return "🔴 Low"

def main():
    # 데이터 로드
    df_tdt, df_panel, df_disclosure = load_data()
    
    # 헤더
    st.markdown('<p class="main-header">🔍 RWA Transparency Dashboard</p>', unsafe_allow_html=True)
    st.markdown("**Transparency Digital Twin (TDT)** - Real-time RWA Risk Monitoring for Exchanges & VCs")
    st.markdown("---")
    
    # 사이드바
    st.sidebar.header("📊 Dashboard Controls")
    
    if not df_tdt.empty:
        # TDT 점수 컬럼 찾기
        tdt_col = 'tdt_equal' if 'tdt_equal' in df_tdt.columns else 'tdt_score'
        
        # 자산 선택
        all_symbols = df_tdt['symbol'].unique().tolist()
        selected_symbols = st.sidebar.multiselect(
            "Select Assets",
            all_symbols,
            default=all_symbols[:5]
        )
        
        # TDT 임계값
        tdt_threshold = st.sidebar.slider("TDT Alert Threshold", 0, 100, 50)
        
        # 필터링
        df_filtered = df_tdt[df_tdt['symbol'].isin(selected_symbols)]
        
        # === 메인 대시보드 ===
        
        # KPI 카드
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_tdt = df_filtered[tdt_col].mean() if not df_filtered.empty else 0
            st.metric(
                label="📈 Average TDT Score",
                value=f"{avg_tdt:.1f}",
                delta=f"{get_score_label(avg_tdt)}"
            )
        
        with col2:
            high_tdt_count = len(df_filtered[df_filtered[tdt_col] >= 70])
            st.metric(
                label="🟢 High Transparency",
                value=f"{high_tdt_count} assets",
                delta=f"{high_tdt_count/len(df_filtered)*100:.0f}%" if len(df_filtered) > 0 else "0%"
            )
        
        with col3:
            low_tdt_count = len(df_filtered[df_filtered[tdt_col] < tdt_threshold])
            st.metric(
                label="🚨 Below Threshold",
                value=f"{low_tdt_count} assets",
                delta="Alert" if low_tdt_count > 0 else "OK",
                delta_color="inverse"
            )
        
        with col4:
            total_mcap = df_filtered['market_cap'].sum() / 1e9 if 'market_cap' in df_filtered.columns else 0
            st.metric(
                label="💰 Total Market Cap",
                value=f"${total_mcap:.1f}B"
            )
        
        st.markdown("---")
        
        # === TDT 점수 분포 ===
        st.subheader("📊 TDT Score Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 바 차트
            fig_bar = px.bar(
                df_filtered.sort_values(tdt_col, ascending=True),
                x=tdt_col,
                y='symbol',
                orientation='h',
                color=tdt_col,
                color_continuous_scale='RdYlGn',
                title="TDT Scores by Asset"
            )
            fig_bar.add_vline(x=tdt_threshold, line_dash="dash", line_color="red",
                             annotation_text=f"Threshold: {tdt_threshold}")
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            # TDT 구성요소 레이더 차트
            if 'latency_score' in df_filtered.columns:
                # 평균 구성요소
                avg_components = {
                    'Latency': df_filtered['latency_score'].mean(),
                    'Completeness': df_filtered['completeness_score'].mean(),
                    'Consistency': df_filtered['consistency_score'].mean()
                }
                
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=list(avg_components.values()),
                    theta=list(avg_components.keys()),
                    fill='toself',
                    name='Average TDT Components'
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title="TDT Component Breakdown (Average)",
                    height=400
                )
                st.plotly_chart(fig_radar, use_container_width=True)
        
        st.markdown("---")
        
        # === 상세 테이블 ===
        st.subheader("📋 Asset Details")
        
        # 테이블 포맷팅
        display_cols = ['symbol', 'name', tdt_col, 'latency_score', 'completeness_score', 'consistency_score']
        display_cols = [c for c in display_cols if c in df_filtered.columns]
        
        # 스타일 함수
        def color_tdt(val):
            if isinstance(val, (int, float)):
                if val >= 70:
                    return 'background-color: #C8E6C9'
                elif val >= 40:
                    return 'background-color: #FFF9C4'
                else:
                    return 'background-color: #FFCDD2'
            return ''
        
        styled_df = df_filtered[display_cols].style.applymap(
            color_tdt, 
            subset=[c for c in [tdt_col, 'latency_score', 'completeness_score', 'consistency_score'] 
                   if c in display_cols]
        )
        st.dataframe(styled_df, use_container_width=True)
        
        st.markdown("---")
        
        # === 리스크 경고 ===
        st.subheader("🚨 Risk Alerts")
        
        low_tdt_assets = df_filtered[df_filtered[tdt_col] < tdt_threshold]
        if len(low_tdt_assets) > 0:
            st.warning(f"**{len(low_tdt_assets)} assets below threshold ({tdt_threshold})**")
            for _, row in low_tdt_assets.iterrows():
                st.error(f"⚠️ **{row['symbol']}**: TDT = {row[tdt_col]:.1f}")
        else:
            st.success("✅ All selected assets are above the TDT threshold")
        
        # === 공시 상세 ===
        if not df_disclosure.empty:
            st.markdown("---")
            st.subheader("📑 Disclosure Details")
            
            with st.expander("View Disclosure Sources"):
                display_cols_disc = ['symbol', 'name', 'transparency_url', 'auditor', 'custodian']
                display_cols_disc = [c for c in display_cols_disc if c in df_disclosure.columns]
                st.dataframe(df_disclosure[display_cols_disc], use_container_width=True)
        
        # === 패널 데이터 시계열 ===
        if not df_panel.empty and 'date' in df_panel.columns:
            st.markdown("---")
            st.subheader("📈 Historical Performance")
            
            selected_symbol = st.selectbox("Select asset for time series", selected_symbols)
            
            df_ts = df_panel[df_panel['symbol'] == selected_symbol].copy()
            df_ts['date'] = pd.to_datetime(df_ts['date'])
            
            if len(df_ts) > 0:
                fig_ts = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                       subplot_titles=('Price', 'Volatility (7d)'))
                
                fig_ts.add_trace(
                    go.Scatter(x=df_ts['date'], y=df_ts['price'], name='Price'),
                    row=1, col=1
                )
                
                if 'volatility_7d' in df_ts.columns:
                    fig_ts.add_trace(
                        go.Scatter(x=df_ts['date'], y=df_ts['volatility_7d'], 
                                  name='Volatility', line=dict(color='red')),
                        row=2, col=1
                    )
                
                fig_ts.update_layout(height=500, title=f"{selected_symbol} Historical Data")
                st.plotly_chart(fig_ts, use_container_width=True)
    
    else:
        st.warning("No data available. Please run the data collection scripts first.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>RWA Transparency Dashboard v1.0 | Built with Streamlit</p>
        <p>Data sources: CoinGecko API, Off-chain Disclosure Analysis</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
