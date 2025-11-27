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


def render_dynamic_indicators(indicators: dict):
    """동적 지표 시각화 섹션"""
    st.subheader("📈 동적 지표 분석")
    st.markdown("시장 변화의 속도와 가속도를 분석합니다.")
    
    # 동적 지표 존재 여부 확인
    dynamic_keys = ['volatility_delta', 'oi_delta', 'funding_delta', 
                    'volatility_accel', 'oi_accel', 'volatility_slope']
    
    has_dynamic = any(k in indicators for k in dynamic_keys)
    
    if not has_dynamic:
        st.info("💡 동적 지표가 없습니다. 하이브리드 모델을 사용하면 동적 지표를 확인할 수 있습니다.")
        return
    
    # OI 데이터 수집 여부 확인
    oi_delta = indicators.get('oi_delta', 0)
    oi_accel = indicators.get('oi_accel', 0)
    has_oi_data = oi_delta != 0 or oi_accel != 0
    
    if not has_oi_data:
        st.warning("⚠️ OI(미결제약정) 데이터가 수집되지 않았습니다. OI 관련 지표는 0으로 표시됩니다.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**변화율 (1차 미분)**")
        
        # 변동성 변화율
        vol_delta = indicators.get('volatility_delta', 0)
        delta_color = "🔴" if vol_delta > 0.01 else ("🟡" if vol_delta > 0 else "🟢")
        st.metric("변동성 변화율", f"{vol_delta:.4f}", delta_color)
        
        # OI 변화율 (데이터 없으면 N/A 표시)
        if has_oi_data:
            delta_color = "🔴" if abs(oi_delta) > 0.1 else "🟢"
            st.metric("OI 변화율", f"{oi_delta:.4f}", delta_color)
        else:
            st.metric("OI 변화율", "N/A", "데이터 없음")
        
        # 펀딩비 변화율
        funding_delta = indicators.get('funding_delta', 0)
        delta_color = "🔴" if abs(funding_delta) > 0.001 else "🟢"
        st.metric("펀딩비 변화율", f"{funding_delta:.6f}", delta_color)
    
    with col2:
        st.markdown("**가속도 (2차 미분)**")
        
        # 변동성 가속도
        vol_accel = indicators.get('volatility_accel', 0)
        accel_color = "🔴" if vol_accel > 0.005 else ("🟡" if vol_accel > 0 else "🟢")
        st.metric("변동성 가속도", f"{vol_accel:.4f}", accel_color)
        
        # OI 가속도 (데이터 없으면 N/A 표시)
        if has_oi_data:
            accel_color = "🔴" if abs(oi_accel) > 0.05 else "🟢"
            st.metric("OI 가속도", f"{oi_accel:.4f}", accel_color)
        else:
            st.metric("OI 가속도", "N/A", "데이터 없음")
        
        # 펀딩비 가속도
        funding_accel = indicators.get('funding_accel', 0)
        accel_color = "🔴" if abs(funding_accel) > 0.0005 else "🟢"
        st.metric("펀딩비 가속도", f"{funding_accel:.6f}", accel_color)
    
    with col3:
        st.markdown("**추세 기울기 (5일)**")
        
        # 변동성 기울기
        vol_slope = indicators.get('volatility_slope', 0)
        slope_direction = "📈 상승" if vol_slope > 0 else "📉 하락"
        st.metric("변동성 기울기", f"{vol_slope:.4f}", slope_direction)
        
        # OI 기울기 (데이터 없으면 N/A 표시)
        oi_slope = indicators.get('oi_slope', 0)
        if has_oi_data:
            slope_direction = "📈 상승" if oi_slope > 0 else "📉 하락"
            st.metric("OI 기울기", f"{oi_slope:.4f}", slope_direction)
        else:
            st.metric("OI 기울기", "N/A", "데이터 없음")
        
        # 펀딩비 기울기
        funding_slope = indicators.get('funding_slope', 0)
        slope_direction = "📈 상승" if funding_slope > 0 else "📉 하락"
        st.metric("펀딩비 기울기", f"{funding_slope:.6f}", slope_direction)
    
    # 동적 지표 해석
    st.markdown("---")
    st.markdown("**📊 동적 지표 해석**")
    
    # 변동성 가속 경고
    vol_accel = indicators.get('volatility_accel', 0)
    vol_delta = indicators.get('volatility_delta', 0)
    
    if vol_accel > 0 and vol_delta > 0:
        st.warning("⚠️ **변동성 급증 중**: 변동성이 가속화되고 있습니다. 포지션 리스크 관리에 주의하세요.")
    elif vol_accel < 0 and vol_delta > 0:
        st.info("ℹ️ **변동성 증가 둔화**: 변동성이 증가하고 있지만 속도가 줄어들고 있습니다.")
    elif vol_delta < 0:
        st.success("✅ **변동성 감소 중**: 시장이 안정화되고 있습니다.")
    
    # OI 변화 경고
    oi_delta = indicators.get('oi_delta', 0)
    funding_delta = indicators.get('funding_delta', 0)
    
    if oi_delta > 0.1 and funding_delta > 0:
        st.warning("⚠️ **롱 포지션 급증**: OI와 펀딩비가 동시에 상승 중입니다. 롱 청산 리스크에 주의하세요.")
    elif oi_delta > 0.1 and funding_delta < 0:
        st.info("ℹ️ **숏 포지션 증가**: OI가 증가하지만 펀딩비가 하락 중입니다. 숏 포지션이 늘어나고 있습니다.")


def render_exchange_flow(data_loader, target_date, coin):
    """거래소 유입/유출 시각화"""
    st.subheader("💹 거래소 유입/유출 분석")
    
    start_date = (target_date - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = target_date.strftime("%Y-%m-%d")
    
    try:
        # whale_daily_stats에서 데이터 로드
        query = f"""
            SELECT date, exchange_inflow_usd, exchange_outflow_usd, net_flow_usd
            FROM whale_daily_stats
            WHERE coin_symbol = '{coin}'
            AND date >= '{start_date}'
            AND date <= '{end_date}'
            ORDER BY date
        """
        
        flow_df = pd.read_sql(query, data_loader.conn)
        
        if len(flow_df) == 0:
            st.info("💡 거래소 유입/유출 데이터가 없습니다.")
            return
        
        flow_df['date'] = pd.to_datetime(flow_df['date'])
        
        # 유입/유출 차트
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=flow_df['date'],
            y=flow_df['exchange_inflow_usd'] / 1e6,
            name='거래소 유입',
            marker_color='red'
        ))
        
        fig.add_trace(go.Bar(
            x=flow_df['date'],
            y=-flow_df['exchange_outflow_usd'] / 1e6,
            name='거래소 유출',
            marker_color='green'
        ))
        
        fig.add_trace(go.Scatter(
            x=flow_df['date'],
            y=flow_df['net_flow_usd'] / 1e6,
            mode='lines',
            name='순유입',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title="거래소 유입/유출 (백만 USD)",
            xaxis_title="날짜",
            yaxis_title="금액 (M USD)",
            barmode='relative',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 요약 통계
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_inflow = flow_df['exchange_inflow_usd'].sum() / 1e6
            st.metric("총 유입", f"${total_inflow:.1f}M")
        
        with col2:
            total_outflow = flow_df['exchange_outflow_usd'].sum() / 1e6
            st.metric("총 유출", f"${total_outflow:.1f}M")
        
        with col3:
            net_flow = flow_df['net_flow_usd'].sum() / 1e6
            flow_direction = "📈" if net_flow > 0 else "📉"
            st.metric("순유입", f"${net_flow:.1f}M", flow_direction)
        
        # 해석
        if net_flow > 0:
            st.warning("⚠️ **순유입 상태**: 고래들이 거래소로 코인을 이동 중입니다. 매도 압력이 증가할 수 있습니다.")
        else:
            st.success("✅ **순유출 상태**: 고래들이 거래소에서 코인을 인출 중입니다. 장기 보유 의향이 있을 수 있습니다.")
    
    except Exception as e:
        st.info(f"💡 거래소 유입/유출 데이터를 불러올 수 없습니다: {str(e)}")


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
        # 사용 가능한 모델 확인
        available_models = []
        model_dir = ROOT / "data" / "models"
        
        if (model_dir / "risk_ai_model.pkl").exists():
            available_models.append("legacy")
        if (model_dir / "hybrid_ensemble_dynamic_metadata.json").exists():
            available_models.append("hybrid")
        
        if not available_models:
            st.error("❌ 사용 가능한 모델이 없습니다.")
            st.info("💡 모델을 먼저 학습시켜야 합니다: `python3 scripts/subprojects/risk_ai/train_model.py`")
            st.stop()
        
        # 기본 모델 타입 선택 (hybrid 우선)
        default_model = "hybrid" if "hybrid" in available_models else "legacy"
        predictor = RiskPredictor(model_type=default_model)
        
    except Exception as e:
        st.error(f"❌ 모델 로드 실패: {str(e)}")
        st.info("💡 모델을 먼저 학습시켜야 합니다: `python3 scripts/subprojects/risk_ai/train_model.py`")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 입력 파라미터")
    
    # 모델 선택 (사용 가능한 모델이 여러 개인 경우)
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
            
            # 동적 지표 섹션 (하이브리드 모델 사용 시)
            if predictor.include_dynamic and not is_weekly:
                st.markdown("---")
                render_dynamic_indicators(indicators)
            
            # 거래소 유입/유출 섹션
            if not is_weekly:
                st.markdown("---")
                render_exchange_flow(data_loader, target_date, coin)
            
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

