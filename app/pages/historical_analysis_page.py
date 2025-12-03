"""
기능 4: 역사적 리스크 분석 페이지
"""

import streamlit as st
from datetime import datetime, date
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
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
from risk_analyzer import RiskAnalyzer


def render():
    st.header("📊 역사적 리스크 분석")
    st.markdown("과거 데이터를 기반으로 리스크 패턴을 분석하고, 모델의 예측 정확도를 확인합니다.")
    
    # 데이터 로더 초기화
    try:
        data_loader = DataLoader()
    except Exception as e:
        st.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        st.stop()
    
    # 리스크 분석기 초기화
    try:
        predictor = RiskPredictor()
        analyzer = RiskAnalyzer()
    except Exception as e:
        st.error(f"❌ 모델 로드 실패: {str(e)}")
        st.info("💡 모델을 먼저 학습시켜야 합니다: `python3 scripts/subprojects/risk_ai/train_model.py`")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 입력 파라미터")
    
    # 기간 선택
    st.sidebar.subheader("📅 기간 설정")
    from_date = st.sidebar.date_input(
        "시작 날짜",
        value=date(2024, 1, 1),
        min_value=date(2023, 1, 1),
        max_value=date.today()
    )
    
    to_date = st.sidebar.date_input(
        "종료 날짜",
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
    
    # 데이터 기준 선택
    st.sidebar.subheader("📊 데이터 기준")
    data_basis = st.sidebar.radio(
        "분석 기준",
        ["일봉 (Daily)", "주봉 (Weekly)"],
        index=0,
        help="일봉: 일별 변동성 분석, 주봉: 주간 추세 기반 분석 (노이즈 감소)"
    )
    is_weekly = data_basis == "주봉 (Weekly)"
    
    # 분석 모드
    st.sidebar.subheader("🔍 분석 모드")
    analysis_mode = st.sidebar.radio(
        "모드",
        ["전체", "고변동성 구간만"],
        index=0
    )
    
    # 분석 실행
    if st.sidebar.button("📊 분석 실행", type="primary"):
        if from_date > to_date:
            st.error("❌ 시작 날짜가 종료 날짜보다 늦습니다.")
            st.stop()
        
        with st.spinner("분석 중..."):
            # 배치 예측
            if is_weekly:
                predictions_df = predictor.predict_batch_weekly(
                    from_date.strftime("%Y-%m-%d"),
                    to_date.strftime("%Y-%m-%d"),
                    coin
                )
            else:
                predictions_df = predictor.predict_batch(
                    from_date.strftime("%Y-%m-%d"),
                    to_date.strftime("%Y-%m-%d"),
                    coin
                )
            
            if len(predictions_df) == 0:
                st.error("❌ 선택한 기간에 데이터가 없습니다.")
                st.stop()
            
            # 리스크 점수 타임라인
            st.subheader("📈 리스크 점수 타임라인")
            
            fig_timeline = go.Figure()
            
            # 예측 리스크 점수
            fig_timeline.add_trace(go.Scatter(
                x=pd.to_datetime(predictions_df['date']),
                y=predictions_df['risk_score'],
                mode='lines+markers',
                name='예측 리스크 점수',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ))
            
            # 실제 고변동성 구간 표시
            if 'actual_high_vol' in predictions_df.columns and predictions_df['actual_high_vol'].notna().any():
                high_vol_dates = predictions_df[predictions_df['actual_high_vol'] == 1]['date']
                high_vol_scores = predictions_df[predictions_df['actual_high_vol'] == 1]['risk_score']
                
                fig_timeline.add_trace(go.Scatter(
                    x=pd.to_datetime(high_vol_dates),
                    y=high_vol_scores,
                    mode='markers',
                    name='실제 고변동성 구간',
                    marker=dict(color='red', size=10, symbol='x')
                ))
            
            # 예측 고변동성 구간 표시 (주봉/일봉에 따라 임계값 다르게)
            if is_weekly:
                threshold = 0.3  # 주봉은 0.3 (더 민감하게)
            else:
                threshold = 0.5  # 일봉은 0.5
            
            predicted_high_vol = predictions_df[predictions_df['high_volatility_prob'] >= threshold]
            if len(predicted_high_vol) > 0:
                fig_timeline.add_trace(go.Scatter(
                    x=pd.to_datetime(predicted_high_vol['date']),
                    y=predicted_high_vol['risk_score'],
                    mode='markers',
                    name=f'예측 고변동성 구간 (임계값 {threshold})',
                    marker=dict(color='orange', size=8, symbol='circle')
                ))
            
            # 기준선
            fig_timeline.add_hline(
                y=70, 
                line_dash="dash", 
                line_color="red", 
                annotation_text="높은 리스크 (70%)"
            )
            fig_timeline.add_hline(
                y=40, 
                line_dash="dash", 
                line_color="yellow", 
                annotation_text="중간 리스크 (40%)"
            )
            
            fig_timeline.update_layout(
                title="리스크 점수 타임라인",
                xaxis_title="날짜",
                yaxis_title="리스크 점수 (%)",
                height=500,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            # 성과 지표
            st.subheader("📊 성과 지표")
            
            if is_weekly:
                performance = analyzer.analyze_historical_performance_weekly(
                    from_date.strftime("%Y-%m-%d"),
                    to_date.strftime("%Y-%m-%d"),
                    coin
                )
            else:
                performance = analyzer.analyze_historical_performance(
                    from_date.strftime("%Y-%m-%d"),
                    to_date.strftime("%Y-%m-%d"),
                    coin
                )
            
            if performance['success']:
                perf_data = performance['data']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**모델 성능**")
                    if perf_data['auc_roc'] is not None:
                        # 실제 고변동성 데이터가 있어서 성과 지표 계산 가능 (일봉/주봉 공통)
                        st.metric("AUC-ROC", f"{perf_data['auc_roc']:.4f}")
                        st.metric("정확도", f"{perf_data['accuracy']:.2%}")
                    else:
                        # 실제 고변동성 데이터가 없어서 기본 통계만 표시
                        if is_weekly:
                            st.info("주봉 분석은 규칙 기반 점수를 사용합니다.")
                        else:
                            st.info("실제 고변동성 데이터가 없어 성능 지표를 계산할 수 없습니다.")
                        
                        if 'avg_risk_score' in perf_data:
                            st.metric("평균 리스크 점수", f"{perf_data['avg_risk_score']:.2f}%")
                            st.metric("최대 리스크 점수", f"{perf_data['max_risk_score']:.2f}%")
                            st.metric("최소 리스크 점수", f"{perf_data['min_risk_score']:.2f}%")
                
                with col2:
                    st.markdown("**예측 정확도**")
                    if perf_data['precision'] is not None:
                        # 실제 고변동성 데이터가 있어서 정확도 계산 가능 (일봉/주봉 공통)
                        st.metric("Precision", f"{perf_data['precision']:.2%}")
                        st.metric("Recall", f"{perf_data['recall']:.2%}")
                        st.metric("F1-Score", f"{perf_data['f1_score']:.4f}")
                    else:
                        # 실제 고변동성 데이터가 없어서 정확도 계산 불가
                        if is_weekly:
                            st.info("주봉 분석은 추세 기반 리스크 점수를 제공합니다.")
                        else:
                            st.info("실제 고변동성 데이터가 없어 정확도를 계산할 수 없습니다.")
                        
                        # 청산 리스크 통계 추가 표시
                        if 'avg_liquidation_risk' in perf_data:
                            st.metric("평균 청산 리스크", f"{perf_data['avg_liquidation_risk']:.2f}%")
                            st.metric("최대 청산 리스크", f"{perf_data['max_liquidation_risk']:.2f}%")
                            st.metric("최소 청산 리스크", f"{perf_data['min_liquidation_risk']:.2f}%")
                
                st.markdown("**통계**")
                col3, col4, col5 = st.columns(3)
                with col3:
                    unit = "주" if is_weekly else "건"
                    st.metric("총 예측 수", f"{perf_data['total_predictions']:,}{unit}")
                with col4:
                    if perf_data['high_vol_count'] is not None:
                        st.metric("실제 고변동성", f"{perf_data['high_vol_count']:,}{unit}")
                    else:
                        st.metric("실제 고변동성", "N/A")
                with col5:
                    st.metric("예측 고변동성", f"{perf_data['predicted_high_vol_count']:,}{unit}")
            
            # 고변동성 구간 목록
            st.subheader("📋 고변동성 구간 목록")
            
            if analysis_mode == "고변동성 구간만":
                if is_weekly:
                    high_vol_df = analyzer.get_high_volatility_periods_weekly(
                        from_date.strftime("%Y-%m-%d"),
                        to_date.strftime("%Y-%m-%d"),
                        coin,
                        threshold=0.5
                    )
                else:
                    high_vol_df = analyzer.get_high_volatility_periods(
                        from_date.strftime("%Y-%m-%d"),
                        to_date.strftime("%Y-%m-%d"),
                        coin,
                        threshold=0.5
                    )
            else:
                high_vol_df = predictions_df.copy()
            
            if len(high_vol_df) > 0:
                # 표시용 DataFrame 생성
                display_df = high_vol_df.copy()
                display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
                display_df['high_volatility_prob'] = (display_df['high_volatility_prob'] * 100).round(2)
                display_df['risk_score'] = display_df['risk_score'].round(2)
                display_df['liquidation_risk'] = display_df['liquidation_risk'].round(2)
                
                # 고변동성 확률과 청산 리스크가 동일한지 확인 (주봉에서 발생할 수 있는 문제)
                if (display_df['high_volatility_prob'] == display_df['liquidation_risk']).all():
                    st.warning("⚠️ 고변동성 확률과 청산 리스크가 동일합니다. 데이터를 확인해주세요.")
                
                if 'actual_high_vol' in display_df.columns:
                    display_df['actual_high_vol'] = display_df['actual_high_vol'].apply(
                        lambda x: "예" if x == 1 else ("아니오" if x == 0 else "N/A")
                    )
                    display_df = display_df.rename(columns={
                        'date': '날짜',
                        'high_volatility_prob': '고변동성 확률 (%)',
                        'risk_score': '리스크 점수 (%)',
                        'liquidation_risk': '청산 리스크 (%)',
                        'actual_high_vol': '실제 고변동성'
                    })
                else:
                    display_df = display_df.rename(columns={
                        'date': '날짜',
                        'high_volatility_prob': '고변동성 확률 (%)',
                        'risk_score': '리스크 점수 (%)',
                        'liquidation_risk': '청산 리스크 (%)'
                    })
                
                st.dataframe(display_df, use_container_width=True, height=400)
            else:
                st.info("고변동성 구간이 없습니다.")
            
            # 지표별 상관관계 분석
            st.subheader("🔍 지표별 상관관계 분석")
            
            if is_weekly:
                corr_matrix = analyzer.calculate_correlation_matrix_weekly(
                    from_date.strftime("%Y-%m-%d"),
                    to_date.strftime("%Y-%m-%d"),
                    coin
                )
            else:
                corr_matrix = analyzer.calculate_correlation_matrix(
                    from_date.strftime("%Y-%m-%d"),
                    to_date.strftime("%Y-%m-%d"),
                    coin
                )
            
            if len(corr_matrix) > 0:
                # NaN이나 inf 값 제거
                corr_matrix_clean = corr_matrix.replace([np.inf, -np.inf], np.nan).dropna(how='all').dropna(axis=1, how='all')
                
                if len(corr_matrix_clean) > 0:
                    fig_heatmap = px.imshow(
                        corr_matrix_clean,
                        labels=dict(x="지표", y="지표", color="상관계수"),
                        x=corr_matrix_clean.columns,
                        y=corr_matrix_clean.columns,
                        color_continuous_scale='RdBu',
                        aspect="auto",
                        title="지표별 상관관계 히트맵"
                    )
                    fig_heatmap.update_layout(height=500)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                    
                    # 상관관계 테이블
                    st.markdown("**상관계수 테이블**")
                    st.dataframe(corr_matrix_clean.round(3), use_container_width=True)
                else:
                    st.warning("⚠️ 변동성 데이터가 없어 상관관계 분석을 수행할 수 없습니다.")
                    st.info("💡 변동성 데이터를 수집하려면 `scripts/subprojects/risk_ai/update_volatility_data.py`를 실행하세요.")
            else:
                st.warning("⚠️ 상관관계 분석을 수행할 수 없습니다.")
                st.info("💡 데이터가 충분하지 않거나 변동성 데이터가 없을 수 있습니다.")
    
    else:
        st.info("👈 사이드바에서 기간과 코인을 선택한 후 '분석 실행' 버튼을 클릭하세요.")

