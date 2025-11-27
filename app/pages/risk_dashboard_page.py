"""
기능 3: 리스크 예측 대시보드 페이지
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


def render():
    st.header("⚠️ 리스크 예측 대시보드")
    st.markdown("현재 시장의 고변동성/청산 리스크를 한눈에 파악합니다.")
    
    # 데이터 로더 초기화
    try:
        data_loader = DataLoader()
    except Exception as e:
        st.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        st.stop()
    
    # 리스크 예측기 초기화
    try:
        predictor = RiskPredictor()
    except Exception as e:
        st.error(f"❌ 모델 로드 실패: {str(e)}")
        st.info("💡 모델을 먼저 학습시켜야 합니다: `python3 scripts/subprojects/risk_ai/train_model.py`")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 입력 파라미터")
    
    # 날짜 선택
    st.sidebar.subheader("📅 날짜 설정")
    target_date = st.sidebar.date_input(
        "예측 날짜",
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
    
    # 예측 실행
    if st.sidebar.button("🔍 리스크 분석", type="primary"):
        with st.spinner("리스크 분석 중..."):
            if is_weekly:
                result = predictor.predict_risk_weekly(target_date.strftime("%Y-%m-%d"), coin)
            else:
                result = predictor.predict_risk(target_date.strftime("%Y-%m-%d"), coin)
            
            if not result['success']:
                st.error(f"❌ {result.get('error', '예측 실패')}")
                if 'closest_date' in result:
                    st.info(f"💡 가장 가까운 날짜: {result['closest_date']}")
                st.stop()
            
            data = result['data']
            
            # 리스크 점수 카드
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
                
                # 게이지 차트
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
                
                # 게이지 차트
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
                
                # 게이지 차트
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
            
            # 주요 지표 카드
            if is_weekly:
                st.subheader("📈 주요 지표 (최근 4주)")
                start_date = (target_date - timedelta(weeks=4)).strftime("%Y-%m-%d")
            else:
                st.subheader("📈 주요 지표 (최근 7일)")
                start_date = (target_date - timedelta(days=7)).strftime("%Y-%m-%d")
            
            end_date = target_date.strftime("%Y-%m-%d")
            
            if is_weekly:
                risk_df = data_loader.load_risk_data_weekly(start_date, end_date, coin)
            else:
                risk_df = data_loader.load_risk_data(start_date, end_date, coin)
            
            if len(risk_df) > 0:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**고래 집중도 변화**")
                    if 'top100_richest_pct' in risk_df.columns:
                        fig1 = px.line(
                            risk_df, 
                            x='date', 
                            y='top100_richest_pct',
                            title="Top 100 지갑 보유 비중",
                            labels={'top100_richest_pct': '보유 비중 (%)', 'date': '날짜'}
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    else:
                        st.info("데이터 없음")
                
                with col2:
                    if is_weekly:
                        st.markdown("**RSI**")
                        if 'rsi' in risk_df.columns:
                            fig2 = px.line(
                                risk_df, 
                                x='date', 
                                y='rsi',
                                title="주간 RSI",
                                labels={'rsi': 'RSI', 'date': '날짜'}
                            )
                            fig2.add_hline(y=70, line_dash="dash", line_color="red")
                            fig2.add_hline(y=30, line_dash="dash", line_color="green")
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.info("데이터 없음")
                    else:
                        st.markdown("**펀딩비**")
                        if 'avg_funding_rate' in risk_df.columns:
                            fig2 = px.line(
                                risk_df, 
                                x='date', 
                                y='avg_funding_rate',
                                title="평균 펀딩비",
                                labels={'avg_funding_rate': '펀딩비 (%)', 'date': '날짜'}
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.info("데이터 없음")
                
                with col3:
                    if is_weekly:
                        st.markdown("**주간 변동폭**")
                        if 'weekly_range_pct' in risk_df.columns:
                            fig3 = px.bar(
                                risk_df, 
                                x='date', 
                                y='weekly_range_pct',
                                title="주간 고저 변동폭 (%)",
                                labels={'weekly_range_pct': '변동폭 (%)', 'date': '날짜'}
                            )
                            st.plotly_chart(fig3, use_container_width=True)
                        else:
                            st.info("데이터 없음")
                    else:
                        st.markdown("**OI 변화율**")
                        if 'sum_open_interest' in risk_df.columns:
                            risk_df['oi_change_7d'] = risk_df['sum_open_interest'].pct_change(7) * 100
                            fig3 = px.line(
                                risk_df, 
                                x='date', 
                                y='oi_change_7d',
                                title="OI 7일 변화율",
                                labels={'oi_change_7d': '변화율 (%)', 'date': '날짜'}
                            )
                            st.plotly_chart(fig3, use_container_width=True)
                        else:
                            st.info("데이터 없음")
            
            # 예측 상세 정보
            st.subheader("🎯 예측 상세 정보")
            
            indicators = data['indicators']
            
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.markdown("**다음날 고변동성 확률**")
                st.metric("확률", f"{high_vol_prob:.1f}%")
                
                st.markdown("**예상 변동성 범위**")
                volatility = indicators.get('volatility_24h', 0) * 100
                st.info(f"현재 변동성: {volatility:.2f}%")
                
                if volatility > 5:
                    st.warning("⚠️ 변동성이 높습니다 (5% 이상)")
                elif volatility > 3:
                    st.info("ℹ️ 변동성이 중간 수준입니다 (3~5%)")
                else:
                    st.success("✅ 변동성이 낮습니다 (3% 미만)")
            
            with info_col2:
                st.markdown("**권장 조치**")
                if risk_score >= 70:
                    st.error("🚨 **포지션 축소 권장**")
                    st.markdown("- 고변동성 가능성이 높습니다")
                    st.markdown("- 리스크 관리에 주의하세요")
                elif risk_score >= 40:
                    st.warning("⚠️ **주의 관찰**")
                    st.markdown("- 리스크가 중간 수준입니다")
                    st.markdown("- 시장 상황을 지속적으로 모니터링하세요")
                else:
                    st.success("✅ **정상 범위**")
                    st.markdown("- 리스크가 낮은 수준입니다")
                    st.markdown("- 일반적인 거래 활동 가능")
            
            # 최근 리스크 이력
            if is_weekly:
                st.subheader("📅 최근 리스크 이력 (최근 12주)")
                history_start = (target_date - timedelta(weeks=12)).strftime("%Y-%m-%d")
            else:
                st.subheader("📅 최근 리스크 이력 (최근 30일)")
                history_start = (target_date - timedelta(days=30)).strftime("%Y-%m-%d")
            
            history_end = target_date.strftime("%Y-%m-%d")
            
            if is_weekly:
                history_df = predictor.predict_batch_weekly(history_start, history_end, coin)
            else:
                history_df = predictor.predict_batch(history_start, history_end, coin)
            
            if len(history_df) > 0:
                fig_history = go.Figure()
                
                fig_history.add_trace(go.Scatter(
                    x=history_df['date'],
                    y=history_df['risk_score'],
                    mode='lines+markers',
                    name='리스크 점수',
                    line=dict(color='blue', width=2)
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
                    height=400
                )
                
                st.plotly_chart(fig_history, use_container_width=True)
            else:
                st.info("최근 30일 데이터가 없습니다.")
    
    else:
        st.info("👈 사이드바에서 날짜와 코인을 선택한 후 '리스크 분석' 버튼을 클릭하세요.")

