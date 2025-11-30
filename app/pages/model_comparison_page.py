"""
모델 성능 비교 페이지
- 모델 성능 비교
- 모델별 예측 결과 비교
- 특성 중요도 비교
"""

import streamlit as st
from datetime import datetime, date, timedelta
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
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
    st.header("🔬 모델 성능 비교")
    st.markdown("여러 모델의 성능을 비교하고 예측 결과를 분석합니다.")
    
    # 데이터 로더 초기화
    try:
        data_loader = DataLoader()
    except Exception as e:
        st.error(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        st.stop()
    
    # 사이드바
    st.sidebar.header("📋 비교 설정")
    
    # 코인 선택
    coin = st.sidebar.selectbox(
        "코인",
        ["BTC", "ETH"],
        index=0
    )
    
    # 날짜 선택
    st.sidebar.subheader("📅 예측 날짜")
    target_date = st.sidebar.date_input(
        "날짜",
        value=date.today(),
        min_value=date(2022, 1, 1),
        max_value=date.today()
    )
    
    # 사용 가능한 모델 확인
    model_dir = ROOT / "data" / "models"
    available_models = []
    
    if (model_dir / "risk_ai_model.pkl").exists():
        available_models.append("legacy")
    
    # 하이브리드 모델 파일 확인
    if (model_dir / "hybrid_ensemble_dynamic_metadata.json").exists():
        available_models.append("hybrid")
    
    if not available_models:
        st.error("❌ 사용 가능한 모델이 없습니다.")
        st.info("💡 모델을 먼저 학습시켜야 합니다.")
        st.info("💡 하이브리드 모델 학습: `python scripts/subprojects/risk_ai/train_hybrid_model.py`")
        st.stop()
    
    # 하이브리드 모델이 없으면 경고
    if "hybrid" not in available_models:
        st.warning("⚠️ 하이브리드 앙상블 모델이 없습니다. 동적 변수 분석 기능이 제한될 수 있습니다.")
        st.info("💡 하이브리드 모델 학습: `python scripts/subprojects/risk_ai/train_hybrid_model.py`")
    
    # 비교할 모델 선택
    st.sidebar.subheader("🤖 비교할 모델")
    selected_models = st.sidebar.multiselect(
        "모델 선택",
        available_models,
        default=available_models,
        format_func=lambda x: {
            "legacy": "XGBoost (정적 변수)",
            "hybrid": "하이브리드 앙상블 (동적 변수 포함)"
        }.get(x, x)
    )
    
    if not selected_models:
        st.warning("⚠️ 최소 1개 모델을 선택하세요.")
        st.stop()
    
    # 비교 실행
    if st.sidebar.button("🔍 모델 비교", type="primary"):
        with st.spinner("모델 비교 중..."):
            # 1. 모델 성능 비교
            st.subheader("📊 모델 성능 비교")
            
            # 평가 결과 파일 로드
            eval_dir = model_dir / "evaluation"
            comparison_file = eval_dir / "model_comparison_summary.csv"
            
            if comparison_file.exists():
                comparison_df = pd.read_csv(comparison_file)
                
                # 선택된 모델만 필터링
                model_mapping = {
                    "XGBoost (Static)": "legacy",
                    "XGBoost (Dynamic)": "hybrid",  # 동적 변수 포함 XGBoost는 hybrid로 매핑
                    "Hybrid Ensemble": "hybrid"
                }
                
                # 매핑되지 않은 모델은 None으로 처리
                comparison_df['model_type'] = comparison_df['Model'].map(model_mapping)
                filtered_df = comparison_df[
                    comparison_df['model_type'].isin(selected_models)
                ].drop('model_type', axis=1)
                
                if len(filtered_df) > 0:
                    # 성능 지표 비교 차트
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # AUC-ROC 비교
                        fig_auc = px.bar(
                            filtered_df,
                            x='Model',
                            y='AUC-ROC',
                            title='AUC-ROC 비교',
                            color='AUC-ROC',
                            color_continuous_scale='Viridis'
                        )
                        fig_auc.update_layout(height=400)
                        st.plotly_chart(fig_auc, use_container_width=True)
                    
                    with col2:
                        # F1 Score 비교
                        fig_f1 = px.bar(
                            filtered_df,
                            x='Model',
                            y='F1',
                            title='F1 Score 비교',
                            color='F1',
                            color_continuous_scale='Plasma'
                        )
                        fig_f1.update_layout(height=400)
                        st.plotly_chart(fig_f1, use_container_width=True)
                    
                    # 성능 지표 테이블
                    st.markdown("**성능 지표 상세**")
                    display_cols = ['Model', 'Accuracy', 'Precision', 'Recall', 'F1', 'AUC-ROC']
                    st.dataframe(filtered_df[display_cols], use_container_width=True)
                else:
                    st.info("선택한 모델의 평가 결과가 없습니다.")
            else:
                st.info("💡 모델 평가 결과 파일이 없습니다. 먼저 모델 평가를 실행하세요.")
            
            st.markdown("---")
            
            # 2. 모델별 예측 결과 비교
            st.subheader("🎯 모델별 예측 결과 비교")
            
            predictions = {}
            
            for model_type in selected_models:
                try:
                    predictor = RiskPredictor(model_type=model_type)
                    result = predictor.predict_risk(target_date.strftime("%Y-%m-%d"), coin)
                    
                    if result['success']:
                        predictions[model_type] = result['data']
                    else:
                        # 데이터가 없으면 없는 것으로 표시 (가장 가까운 날짜 사용하지 않음)
                        st.warning(f"⚠️ {model_type} 모델: {target_date} 데이터 없음 - {result.get('error', '알 수 없음')}")
                except Exception as e:
                    st.warning(f"⚠️ {model_type} 모델 예측 실패: {str(e)}")
            
            if len(predictions) > 0:
                # 예측 결과 비교 차트
                fig_comparison = go.Figure()
                
                model_names = {
                    "legacy": "XGBoost (정적)",
                    "hybrid": "하이브리드 앙상블"
                }
                
                metrics = ['high_volatility_prob', 'liquidation_risk', 'risk_score']
                metric_labels = {
                    'high_volatility_prob': '고변동성 확률',
                    'liquidation_risk': '청산 리스크',
                    'risk_score': '종합 리스크'
                }
                
                for metric in metrics:
                    values = [predictions[m].get(metric, 0) * 100 if metric == 'high_volatility_prob' 
                             else predictions[m].get(metric, 0) for m in predictions.keys()]
                    fig_comparison.add_trace(go.Bar(
                        x=[model_names.get(m, m) for m in predictions.keys()],
                        y=values,
                        name=metric_labels[metric]
                    ))
                
                fig_comparison.update_layout(
                    title=f'{target_date} 예측 결과 비교',
                    xaxis_title='모델',
                    yaxis_title='점수 (%)',
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                # 예측 결과 테이블
                st.markdown("**예측 결과 상세**")
                comparison_data = []
                for model_type, pred in predictions.items():
                    comparison_data.append({
                        '모델': model_names.get(model_type, model_type),
                        '고변동성 확률': f"{pred.get('high_volatility_prob', 0) * 100:.1f}%",
                        '청산 리스크': f"{pred.get('liquidation_risk', 0):.1f}%",
                        '종합 리스크': f"{pred.get('risk_score', 0):.1f}%"
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, use_container_width=True)
            else:
                st.error("❌ 예측 결과를 가져올 수 없습니다.")
            
            st.markdown("---")
            
            # 3. 특성 중요도 비교
            st.subheader("📊 특성 중요도 비교")
            
            importance_file = ROOT / "data" / "models" / "evaluation" / "feature_importance.csv"
            if importance_file.exists():
                importance_df = pd.read_csv(importance_file)
                
                # 상위 15개 특성
                top_features = importance_df.head(15)
                
                # 동적 변수 vs 정적 변수 구분
                top_features['변수 타입'] = top_features['feature'].apply(
                    lambda x: '동적 변수' if any(k in x for k in ['delta', 'accel', 'slope', 'momentum', 'stability']) 
                    else '정적 변수'
                )
                
                # 바 차트
                fig_importance = px.bar(
                    top_features,
                    x='importance',
                    y='feature',
                    orientation='h',
                    color='변수 타입',
                    title='특성 중요도 (상위 15개)',
                    labels={'importance': '중요도', 'feature': '변수'},
                    color_discrete_map={'동적 변수': '#1f77b4', '정적 변수': '#ff7f0e'}
                )
                fig_importance.update_layout(height=500)
                st.plotly_chart(fig_importance, use_container_width=True)
                
                # 동적 변수 기여도
                dynamic_importance = top_features[top_features['변수 타입'] == '동적 변수']['importance'].sum()
                total_importance = top_features['importance'].sum()
                contribution_pct = (dynamic_importance / total_importance * 100) if total_importance > 0 else 0
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("동적 변수 중요도 합계", f"{dynamic_importance:.4f}")
                with col2:
                    st.metric("전체 대비 기여도", f"{contribution_pct:.1f}%")
            else:
                st.info("💡 특성 중요도 파일이 없습니다.")
    
    else:
        st.info("👈 사이드바에서 설정을 선택한 후 '모델 비교' 버튼을 클릭하세요.")

