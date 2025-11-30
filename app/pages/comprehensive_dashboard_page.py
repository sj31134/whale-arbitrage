"""
리스크 분석 종합 대시보드
- 현재 리스크 예측
- 파생상품 지표
- 동적 변수 분석
- 모델 성능 비교
- 거래소 유입/유출
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
from risk_predictor import RiskPredictor

# risk_dashboard_page의 함수들을 직접 import
try:
    from app.pages import risk_dashboard_page
except ImportError:
    from pages import risk_dashboard_page

render_dynamic_indicators = risk_dashboard_page.render_dynamic_indicators
render_derivatives_metrics = risk_dashboard_page.render_derivatives_metrics
render_exchange_flow = risk_dashboard_page.render_exchange_flow


def render():
    st.header("📊 리스크 분석 종합 대시보드")
    st.markdown("모든 리스크 분석 기능을 한 화면에서 확인합니다.")
    
    # 데이터 로더 초기화
    try:
        data_loader = DataLoader()
    except Exception as e:
        st.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        st.stop()
    
    # 리스크 예측기 초기화
    try:
        model_dir = ROOT / "data" / "models"
        available_models = []
        
        if (model_dir / "risk_ai_model.pkl").exists():
            available_models.append("legacy")
        if (model_dir / "hybrid_ensemble_dynamic_metadata.json").exists():
            available_models.append("hybrid")
        
        if not available_models:
            st.error("❌ 사용 가능한 모델이 없습니다.")
            st.stop()
        
        default_model = "hybrid" if "hybrid" in available_models else "legacy"
        predictor = RiskPredictor(model_type=default_model)
        
    except Exception as e:
        st.error(f"❌ 모델 로드 실패: {str(e)}")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 설정")
    
    # 모델 선택
    if len(available_models) > 1:
        st.sidebar.subheader("🤖 모델 선택")
        model_labels = {
            "legacy": "XGBoost (기본)",
            "hybrid": "하이브리드 앙상블 (권장)"
        }
        selected_model = st.sidebar.selectbox(
            "예측 모델",
            available_models,
            format_func=lambda x: model_labels.get(x, x),
            index=available_models.index(default_model) if default_model in available_models else 0
        )
        
        if selected_model != predictor.model_type:
            predictor = RiskPredictor(model_type=selected_model)
    
    # 날짜 선택
    st.sidebar.subheader("📅 날짜 설정")
    target_date = st.sidebar.date_input(
        "예측 날짜",
        value=date.today(),
        min_value=date(2022, 1, 1),
        max_value=date.today()
    )
    
    # 코인 선택
    st.sidebar.subheader("💰 코인 선택")
    coin = st.sidebar.selectbox(
        "코인",
        ["BTC", "ETH"],
        index=0
    )
    
    # 분석 실행
    if st.sidebar.button("🔍 종합 분석 실행", type="primary"):
        with st.spinner("종합 분석 중..."):
            # 1. 리스크 점수 카드 (대형)
            result = predictor.predict_risk(target_date.strftime("%Y-%m-%d"), coin)
            
            if not result['success']:
                st.error(f"❌ {result.get('error', '예측 실패')}")
                st.stop()
            
            data = result['data']
            
            st.subheader("📊 현재 리스크 점수")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                high_vol_prob = data['high_volatility_prob'] * 100
                risk_level = "낮음" if high_vol_prob < 40 else ("중간" if high_vol_prob < 70 else "높음")
                risk_color = "🟢" if high_vol_prob < 40 else ("🟡" if high_vol_prob < 70 else "🔴")
                
                st.metric(
                    "고변동성 확률",
                    f"{high_vol_prob:.1f}%",
                    f"{risk_level} {risk_color}"
                )
                
                fig_gauge1 = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = high_vol_prob,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "고변동성 확률"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 40], 'color': "lightgreen"},
                            {'range': [40, 70], 'color': "yellow"},
                            {'range': [70, 100], 'color': "lightcoral"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 70
                        }
                    }
                ))
                fig_gauge1.update_layout(height=250)
                st.plotly_chart(fig_gauge1, use_container_width=True)
            
            with col2:
                liquidation_risk = data['liquidation_risk']
                risk_level = "낮음" if liquidation_risk < 40 else ("중간" if liquidation_risk < 70 else "높음")
                risk_color = "🟢" if liquidation_risk < 40 else ("🟡" if liquidation_risk < 70 else "🔴")
                
                st.metric(
                    "청산 리스크",
                    f"{liquidation_risk:.1f}%",
                    f"{risk_level} {risk_color}"
                )
                
                fig_gauge2 = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = liquidation_risk,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "청산 리스크"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 40], 'color': "lightgreen"},
                            {'range': [40, 70], 'color': "yellow"},
                            {'range': [70, 100], 'color': "lightcoral"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 70
                        }
                    }
                ))
                fig_gauge2.update_layout(height=250)
                st.plotly_chart(fig_gauge2, use_container_width=True)
            
            with col3:
                risk_score = data['risk_score']
                risk_level = "낮음" if risk_score < 40 else ("중간" if risk_score < 70 else "높음")
                risk_color = "🟢" if risk_score < 40 else ("🟡" if risk_score < 70 else "🔴")
                
                st.metric(
                    "종합 리스크",
                    f"{risk_score:.1f}%",
                    f"{risk_level} {risk_color}"
                )
                
                fig_gauge3 = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = risk_score,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "종합 리스크"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 40], 'color': "lightgreen"},
                            {'range': [40, 70], 'color': "yellow"},
                            {'range': [70, 100], 'color': "lightcoral"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 70
                        }
                    }
                ))
                fig_gauge3.update_layout(height=250)
                st.plotly_chart(fig_gauge3, use_container_width=True)
            
            st.markdown("---")
            
            # 2. 파생상품 지표 & 동적 변수 분석 (2열)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📈 파생상품 지표")
                render_derivatives_metrics(data_loader, target_date, coin)
            
            with col2:
                st.markdown("### 📉 동적 변수 분석")
                if predictor.include_dynamic:
                    indicators = data['indicators']
                    render_dynamic_indicators(indicators, data_loader, target_date, coin)
                else:
                    st.info("💡 동적 변수 분석을 보려면 하이브리드 모델을 사용하세요.")
            
            st.markdown("---")
            
            # 3. 거래소 유입/유출
            st.markdown("### 💰 거래소 유입/유출")
            render_exchange_flow(data_loader, target_date, coin)
            
            st.markdown("---")
            
            # 4. 고래 데이터 가격 상관관계 분석
            st.markdown("### 🔗 고래 데이터 가격 상관관계")
            
            analysis_dir = ROOT / "data" / "analysis"
            whale_corr_files = list(analysis_dir.glob(f"whale_price_correlation_{coin}_*.csv"))
            
            if whale_corr_files:
                latest_file = max(whale_corr_files, key=lambda p: p.stat().st_mtime)
                whale_corr = pd.read_csv(latest_file)
                
                # 유의미한 상관관계만 필터링
                significant = whale_corr[
                    (whale_corr['pearson_pvalue'] < 0.05) &
                    (whale_corr['sample_size'] >= 30)
                ].copy()
                
                if len(significant) > 0:
                    st.info(f"💡 분석 결과: {len(significant)}개 유의미한 상관관계 발견")
                    
                    # 타겟별 상위 변수
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # price_change_1d 상위 변수
                        price_1d = significant[significant['target'] == 'price_change_1d'].nlargest(5, 'pearson_correlation')
                        if len(price_1d) > 0:
                            fig = px.bar(
                                price_1d,
                                x='variable',
                                y='pearson_correlation',
                                title='1일 후 가격 변화율 상관관계',
                                labels={'pearson_correlation': '상관계수', 'variable': '변수'}
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # price_static 상위 변수
                        price_static = significant[significant['target'] == 'price_static'].nlargest(5, 'pearson_correlation')
                        if len(price_static) > 0:
                            fig = px.bar(
                                price_static,
                                x='variable',
                                y='pearson_correlation',
                                title='가격(정적) 상관관계',
                                labels={'pearson_correlation': '상관계수', 'variable': '변수'}
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    # 상세 결과 테이블
                    with st.expander("상세 상관관계 결과"):
                        display_cols = ['variable', 'target', 'lag', 'pearson_correlation', 'pearson_pvalue', 'sample_size']
                        if 'r_squared' in significant.columns:
                            display_cols.append('r_squared')
                        st.dataframe(
                            significant[display_cols].sort_values('pearson_correlation', ascending=False).head(20).round(4),
                            use_container_width=True
                        )
                else:
                    st.warning("⚠️ 유의미한 상관관계가 없습니다.")
            else:
                st.info("💡 고래 데이터 상관관계 분석 결과가 없습니다.")
                st.code(f"python scripts/subprojects/risk_ai/analyze_whale_price_correlation.py --coin {coin} --start-date 2022-01-01")
            
            st.markdown("---")
            
            # 5. 최근 리스크 이력
            st.markdown("### 📅 최근 리스크 이력 (30일)")
            history_start = (target_date - timedelta(days=30)).strftime("%Y-%m-%d")
            history_end = target_date.strftime("%Y-%m-%d")
            
            history_df = predictor.predict_batch(history_start, history_end, coin)
            
            if len(history_df) > 0:
                fig_history = go.Figure()
                
                fig_history.add_trace(go.Scatter(
                    x=history_df['date'],
                    y=history_df['risk_score'],
                    mode='lines+markers',
                    name='종합 리스크',
                    line=dict(color='blue', width=2)
                ))
                
                fig_history.add_trace(go.Scatter(
                    x=history_df['date'],
                    y=history_df['high_volatility_prob'] * 100,
                    mode='lines',
                    name='고변동성 확률',
                    line=dict(color='red', width=1, dash='dash')
                ))
                
                fig_history.add_trace(go.Scatter(
                    x=history_df['date'],
                    y=history_df['liquidation_risk'],
                    mode='lines',
                    name='청산 리스크',
                    line=dict(color='orange', width=1, dash='dot')
                ))
                
                fig_history.add_hline(
                    y=70, 
                    line_dash="dash", 
                    line_color="red", 
                    annotation_text="높은 리스크 (70%)"
                )
                fig_history.add_hline(
                    y=40, 
                    line_dash="dash", 
                    line_color="yellow", 
                    annotation_text="중간 리스크 (40%)"
                )
                
                fig_history.update_layout(
                    title="30일 리스크 점수 타임라인",
                    xaxis_title="날짜",
                    yaxis_title="리스크 점수 (%)",
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_history, use_container_width=True)
            else:
                st.info("최근 30일 데이터가 없습니다.")
    
    else:
        st.info("👈 사이드바에서 날짜와 코인을 선택한 후 '종합 분석 실행' 버튼을 클릭하세요.")

