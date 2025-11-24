"""
기능 5: 특성 중요도 분석 페이지
"""

import streamlit as st
from datetime import datetime, date
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

from feature_explainer import FeatureExplainer


def render():
    st.header("🔍 특성 중요도 분석")
    st.markdown("모델이 어떤 지표를 중요하게 보는지 분석하고, 예측 근거를 설명합니다.")
    
    # 특성 설명기 초기화
    try:
        explainer = FeatureExplainer()
    except Exception as e:
        st.error(f"❌ 모델 로드 실패: {str(e)}")
        st.info("💡 모델을 먼저 학습시켜야 합니다: `python3 scripts/subprojects/risk_ai/train_model.py`")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 입력 파라미터")
    
    # 분석 날짜
    st.sidebar.subheader("📅 분석 날짜")
    analysis_date = st.sidebar.date_input(
        "특정 예측 분석용 날짜",
        value=date.today(),
        min_value=date(2023, 1, 1),
        max_value=date.today()
    )
    
    # 코인 선택
    st.sidebar.subheader("💰 코인 선택")
    coin = st.sidebar.selectbox(
        "코인",
        ["BTC", "ETH"],
        index=0
    )
    
    # 특성 개수
    st.sidebar.subheader("🔢 특성 개수")
    top_n = st.sidebar.slider(
        "상위 N개 특성",
        min_value=5,
        max_value=20,
        value=10,
        step=1
    )
    
    # 특성 중요도
    st.subheader("📊 특성 중요도 (Feature Importance)")
    
    importance_df = explainer.get_feature_importance(top_n=top_n)
    
    if len(importance_df) > 0:
        # Horizontal Bar Chart
        fig_bar = px.bar(
            importance_df,
            x='importance',
            y='feature',
            orientation='h',
            title=f"상위 {len(importance_df)}개 특성 중요도",
            labels={'importance': '중요도', 'feature': '특성'},
            color='importance',
            color_continuous_scale='Blues'
        )
        fig_bar.update_layout(
            height=max(400, len(importance_df) * 40),
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 특성 중요도 테이블
        st.markdown("**특성 중요도 상세**")
        display_df = importance_df.copy()
        display_df['importance'] = display_df['importance'].round(2)
        display_df = display_df.rename(columns={
            'feature': '특성',
            'importance': '중요도'
        })
        st.dataframe(display_df, use_container_width=True)
    else:
        st.error("특성 중요도를 가져올 수 없습니다.")
        st.stop()
    
    # SHAP 값 분석
    st.subheader("🎯 SHAP 값 분석 (예측 설명)")
    
    if not explainer.shap_available:
        st.warning("⚠️ SHAP가 설치되어 있지 않습니다. SHAP 분석을 사용하려면 `pip install shap`을 실행하세요.")
    else:
        if st.button("🔍 SHAP 분석 실행", type="primary"):
            with st.spinner("SHAP 값 계산 중..."):
                shap_result = explainer.explain_prediction(
                    analysis_date.strftime("%Y-%m-%d"),
                    coin
                )
                
                if shap_result['success']:
                    shap_data = shap_result['data']
                    
                    # Waterfall Chart
                    shap_values = shap_data['shap_values']
                    base_value = shap_data['base_value']
                    prediction = shap_data['prediction']
                    
                    # SHAP 값 정렬
                    sorted_shap = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)
                    
                    # Waterfall Chart 데이터 준비
                    features = [item[0] for item in sorted_shap]
                    values = [item[1] for item in sorted_shap]
                    
                    # Waterfall Chart
                    fig_waterfall = go.Figure(go.Waterfall(
                        orientation="v",
                        measure=["absolute"] + ["relative"] * len(features) + ["total"],
                        x=["기준값"] + features + ["예측값"],
                        textposition="outside",
                        text=[f"{base_value:.4f}"] + [f"{v:+.4f}" for v in values] + [f"{prediction:.4f}"],
                        y=[base_value] + values + [0],
                        connector={"line": {"color": "rgb(63, 63, 63)"}},
                    ))
                    
                    fig_waterfall.update_layout(
                        title=f"{analysis_date} 예측에 대한 SHAP 값 분석",
                        showlegend=False,
                        height=600
                    )
                    
                    st.plotly_chart(fig_waterfall, use_container_width=True)
                    
                    # SHAP 값 테이블
                    st.markdown("**SHAP 값 상세**")
                    shap_df = pd.DataFrame({
                        '특성': features,
                        'SHAP 값': [round(v, 4) for v in values],
                        '기여도': [f"{v:+.4f}" for v in values]
                    })
                    st.dataframe(shap_df, use_container_width=True)
                    
                    st.info(f"**기준값**: {base_value:.4f}, **예측 확률**: {prediction:.4f}")
                else:
                    st.error(f"❌ {shap_result.get('error', 'SHAP 분석 실패')}")
    
    # 특성별 분포 및 영향
    st.subheader("📈 특성별 분포 및 영향 (Partial Dependence)")
    
    # 주요 특성 선택
    if len(importance_df) > 0:
        top_features = importance_df.head(4)['feature'].tolist()
        
        selected_feature = st.selectbox(
            "분석할 특성 선택",
            top_features,
            index=0
        )
        
        if st.button("📊 Partial Dependence 분석", type="primary"):
            with st.spinner("Partial Dependence 계산 중..."):
                pdp_df = explainer.get_partial_dependence(selected_feature, coin)
                
                if len(pdp_df) > 0:
                    fig_pdp = px.line(
                        pdp_df,
                        x='feature_value',
                        y='prediction',
                        title=f"{selected_feature}에 대한 Partial Dependence Plot",
                        labels={
                            'feature_value': f'{selected_feature} 값',
                            'prediction': '예측 확률 (고변동성)'
                        },
                        markers=True
                    )
                    fig_pdp.update_layout(height=400)
                    st.plotly_chart(fig_pdp, use_container_width=True)
                    
                    st.markdown("**해석**")
                    st.info(f"이 차트는 {selected_feature} 값이 변할 때 예측 확률이 어떻게 변하는지 보여줍니다.")
                else:
                    st.error("Partial Dependence 데이터를 계산할 수 없습니다.")
    
    # 특정 예측 분석
    st.subheader("🔬 특정 예측 분석")
    
    if st.button("🔍 예측 상세 분석", type="primary"):
        with st.spinner("예측 분석 중..."):
            from risk_predictor import RiskPredictor
            predictor = RiskPredictor()
            
            result = predictor.predict_risk(
                analysis_date.strftime("%Y-%m-%d"),
                coin
            )
            
            if result['success']:
                data = result['data']
                indicators = data['indicators']
                
                st.markdown(f"**{analysis_date} 예측 결과**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("고변동성 확률", f"{data['high_volatility_prob']*100:.1f}%")
                    st.metric("종합 리스크 점수", f"{data['risk_score']:.1f}%")
                    st.metric("청산 리스크", f"{data['liquidation_risk']:.1f}%")
                
                with col2:
                    st.markdown("**주요 지표**")
                    st.json({
                        '고래 집중도 변화 (7일)': f"{indicators.get('whale_conc_change_7d', 0):.4f}",
                        '펀딩비': f"{indicators.get('funding_rate', 0):.6f}",
                        '펀딩비 Z-Score': f"{indicators.get('funding_rate_zscore', 0):.2f}",
                        'OI 변화율 (7일)': f"{indicators.get('oi_growth_7d', 0):.4f}",
                        '변동성 (24h)': f"{indicators.get('volatility_24h', 0)*100:.2f}%"
                    })
            else:
                st.error(f"❌ {result.get('error', '예측 실패')}")

