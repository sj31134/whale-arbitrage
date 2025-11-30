"""
동적 변수 분석 페이지
- 동적 변수 시계열 분석
- 동적 변수 상관관계
- 동적 변수 기여도
- 동적 변수 예측력 분석
"""

import streamlit as st
from datetime import datetime, date, timedelta
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
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from data_loader import DataLoader
from feature_engineering import FeatureEngineer


def render():
    st.header("📈 동적 변수 분석")
    st.markdown("시장 변화의 속도(변화율), 가속도, 추세(기울기) 등 동적 변수를 분석합니다.")
    
    # 데이터 로더 초기화
    try:
        data_loader = DataLoader()
        feature_engineer = FeatureEngineer()
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
        min_value=30,
        max_value=365,
        value=90,
        step=30
    )
    
    start_date = end_date - timedelta(days=days_back)
    
    # 분석 실행
    if st.sidebar.button("🔍 분석 실행", type="primary"):
        with st.spinner("동적 변수 계산 중..."):
            # 원본 데이터 로드
            raw_df = feature_engineer.load_raw_data(start_date.strftime("%Y-%m-%d"))
            
            if raw_df.empty:
                st.error("❌ 데이터를 불러올 수 없습니다.")
                st.stop()
            
            # 동적 변수 포함 피처 생성
            df_features, features = feature_engineer.create_features(raw_df, include_dynamic=True)
            
            if df_features.empty:
                st.error("❌ 피처 생성 실패")
                st.stop()
            
            # 동적 변수 필터링
            dynamic_features = [f for f in features if any(x in f for x in ['delta', 'accel', 'slope', 'momentum', 'stability'])]
            
            st.success(f"✅ {len(dynamic_features)}개 동적 변수 계산 완료")
            
            # 1. 동적 변수 시계열 분석
            st.subheader("📊 동적 변수 시계열 분석")
            
            # 변화율 (Delta) 변수
            delta_features = [f for f in dynamic_features if 'delta' in f and 'stability' not in f]
            if delta_features:
                st.markdown("**변화율 (1차 미분)**")
                fig_delta = go.Figure()
                
                for feat in delta_features[:5]:  # 상위 5개만
                    if feat in df_features.columns:
                        fig_delta.add_trace(go.Scatter(
                            x=df_features['date'],
                            y=df_features[feat],
                            mode='lines',
                            name=feat,
                            line=dict(width=1.5)
                        ))
                
                fig_delta.update_layout(
                    title='변화율 추이',
                    xaxis_title='날짜',
                    yaxis_title='변화율',
                    height=400,
                    hovermode='x unified'
                )
                fig_delta.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_delta, use_container_width=True)
            
            # 가속도 (Acceleration) 변수
            accel_features = [f for f in dynamic_features if 'accel' in f]
            if accel_features:
                st.markdown("**가속도 (2차 미분)**")
                fig_accel = go.Figure()
                
                for feat in accel_features[:5]:  # 상위 5개만
                    if feat in df_features.columns:
                        fig_accel.add_trace(go.Scatter(
                            x=df_features['date'],
                            y=df_features[feat],
                            mode='lines',
                            name=feat,
                            line=dict(width=1.5)
                        ))
                
                fig_accel.update_layout(
                    title='가속도 추이',
                    xaxis_title='날짜',
                    yaxis_title='가속도',
                    height=400,
                    hovermode='x unified'
                )
                fig_accel.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_accel, use_container_width=True)
            
            # 기울기 (Slope) 변수
            slope_features = [f for f in dynamic_features if 'slope' in f]
            if slope_features:
                st.markdown("**추세 기울기 (5일 이동평균)**")
                fig_slope = go.Figure()
                
                for feat in slope_features[:5]:  # 상위 5개만
                    if feat in df_features.columns:
                        fig_slope.add_trace(go.Scatter(
                            x=df_features['date'],
                            y=df_features[feat],
                            mode='lines',
                            name=feat,
                            line=dict(width=1.5)
                        ))
                
                fig_slope.update_layout(
                    title='추세 기울기 추이',
                    xaxis_title='날짜',
                    yaxis_title='기울기',
                    height=400,
                    hovermode='x unified'
                )
                fig_slope.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_slope, use_container_width=True)
            
            st.markdown("---")
            
            # 2. 동적 변수와 가격 상관관계 분석
            st.subheader("🔗 동적 변수와 가격 상관관계")
            
            # 분석 결과 파일 로드
            analysis_dir = ROOT / "data" / "analysis"
            correlation_files = list(analysis_dir.glob(f"dynamic_correlation_{coin}_*.csv"))
            
            if correlation_files:
                # 가장 최신 파일 사용
                latest_file = max(correlation_files, key=lambda p: p.stat().st_mtime)
                corr_results = pd.read_csv(latest_file)
                
                # 유의미한 상관관계만 필터링 (p < 0.05)
                significant = corr_results[
                    (corr_results['pearson_pvalue'] < 0.05) &
                    (corr_results['sample_size'] >= 30)
                ].copy()
                
                if len(significant) > 0:
                    st.info(f"💡 분석 결과 파일: {latest_file.name}")
                    st.info(f"   유의미한 상관관계: {len(significant)}개 (p < 0.05)")
                    
                    # 타겟별 그룹화
                    for target in ['price_change_1d', 'price_change_7d', 'volatility_change_1d', 'price_direction_1d']:
                        target_data = significant[significant['target'] == target]
                        if len(target_data) > 0:
                            st.markdown(f"**{target}**")
                            top5 = target_data.nlargest(5, 'pearson_correlation', keep='all')
                            
                            fig = px.bar(
                                top5,
                                x='variable',
                                y='pearson_correlation',
                                color='pearson_correlation',
                                color_continuous_scale='RdBu',
                                title=f'{target}와의 상관관계 (상위 5개)',
                                labels={'pearson_correlation': '상관계수', 'variable': '동적 변수'}
                            )
                            fig.update_layout(height=300, showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # 상세 테이블
                            with st.expander(f"{target} 상세 결과"):
                                st.dataframe(
                                    top5[['variable', 'lag', 'pearson_correlation', 'pearson_pvalue', 'sample_size']].round(4),
                                    use_container_width=True
                                )
                else:
                    st.warning("⚠️ 유의미한 상관관계가 없습니다. 분석을 먼저 실행하세요.")
                    st.code(f"python scripts/subprojects/risk_ai/analyze_dynamic_correlation.py --coin {coin}")
            else:
                st.info("💡 상관관계 분석 결과가 없습니다.")
                st.code(f"python scripts/subprojects/risk_ai/analyze_dynamic_correlation.py --coin {coin} --start-date {start_date.strftime('%Y-%m-%d')}")
            
            st.markdown("---")
            
            # 3. 백테스트 결과
            st.subheader("📈 동적 변수 백테스트 결과")
            
            backtest_files = list(analysis_dir.glob(f"dynamic_backtest_{coin}_*.csv"))
            
            if backtest_files:
                latest_backtest = max(backtest_files, key=lambda p: p.stat().st_mtime)
                backtest_results = pd.read_csv(latest_backtest)
                
                st.info(f"💡 백테스트 결과 파일: {latest_backtest.name}")
                
                # 상위 10개 최고 수익률
                top10 = backtest_results.nlargest(10, 'total_return', keep='all')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_return = px.bar(
                        top10,
                        x='variable',
                        y='total_return',
                        color='total_return',
                        color_continuous_scale='Viridis',
                        title='총 수익률 (상위 10개)',
                        labels={'total_return': '총 수익률', 'variable': '동적 변수'}
                    )
                    fig_return.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_return, use_container_width=True)
                
                with col2:
                    fig_sharpe = px.bar(
                        top10,
                        x='variable',
                        y='sharpe_ratio',
                        color='sharpe_ratio',
                        color_continuous_scale='Plasma',
                        title='Sharpe Ratio (상위 10개)',
                        labels={'sharpe_ratio': 'Sharpe Ratio', 'variable': '동적 변수'}
                    )
                    fig_sharpe.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_sharpe, use_container_width=True)
                
                # 상세 테이블
                with st.expander("백테스트 상세 결과"):
                    st.dataframe(
                        top10[['variable', 'threshold', 'direction', 'total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'total_trades']].round(4),
                        use_container_width=True
                    )
            else:
                st.info("💡 백테스트 결과가 없습니다.")
                st.code(f"python scripts/subprojects/risk_ai/backtest_dynamic_signals.py --coin {coin} --start-date {start_date.strftime('%Y-%m-%d')}")
            
            st.markdown("---")
            
            # 4. 동적 변수 간 상관관계
            st.subheader("🔗 동적 변수 간 상관관계")
            
            if len(dynamic_features) > 0:
                # 상관관계 계산
                dynamic_df = df_features[['date'] + [f for f in dynamic_features if f in df_features.columns]]
                corr_df = dynamic_df.drop('date', axis=1).corr()
                
                # 히트맵
                fig_corr = px.imshow(
                    corr_df,
                    title='동적 변수 상관관계 히트맵',
                    color_continuous_scale='RdBu',
                    aspect='auto',
                    labels=dict(color="상관계수")
                )
                st.plotly_chart(fig_corr, use_container_width=True)
                
                # 높은 상관관계 쌍 찾기
                st.markdown("**높은 상관관계 변수 쌍 (|r| > 0.7)**")
                high_corr_pairs = []
                for i in range(len(corr_df.columns)):
                    for j in range(i+1, len(corr_df.columns)):
                        corr_val = corr_df.iloc[i, j]
                        if abs(corr_val) > 0.7:
                            high_corr_pairs.append({
                                '변수1': corr_df.columns[i],
                                '변수2': corr_df.columns[j],
                                '상관계수': corr_val
                            })
                
                if high_corr_pairs:
                    high_corr_df = pd.DataFrame(high_corr_pairs)
                    st.dataframe(high_corr_df, use_container_width=True)
                else:
                    st.info("높은 상관관계 변수 쌍이 없습니다.")
            
            st.markdown("---")
            
            # 3. 동적 변수 기여도
            st.subheader("📊 동적 변수 기여도")
            
            # 특성 중요도 파일 로드 시도
            importance_file = ROOT / "data" / "models" / "evaluation" / "feature_importance.csv"
            if importance_file.exists():
                importance_df = pd.read_csv(importance_file)
                
                # 동적 변수만 필터링
                dynamic_importance = importance_df[
                    importance_df['feature'].str.contains('delta|accel|slope|momentum|stability', case=False, na=False)
                ].sort_values('importance', ascending=False)
                
                if len(dynamic_importance) > 0:
                    # 바 차트
                    fig_importance = px.bar(
                        dynamic_importance.head(10),
                        x='importance',
                        y='feature',
                        orientation='h',
                        title='동적 변수 중요도 (상위 10개)',
                        labels={'importance': '중요도', 'feature': '변수'}
                    )
                    fig_importance.update_layout(height=400)
                    st.plotly_chart(fig_importance, use_container_width=True)
                    
                    # 총 기여도
                    total_importance = dynamic_importance['importance'].sum()
                    all_importance = importance_df['importance'].sum()
                    contribution_pct = (total_importance / all_importance * 100) if all_importance > 0 else 0
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("동적 변수 총 중요도", f"{total_importance:.4f}")
                    with col2:
                        st.metric("전체 대비 기여도", f"{contribution_pct:.1f}%")
                else:
                    st.info("동적 변수 중요도 데이터가 없습니다.")
            else:
                st.info("💡 특성 중요도 파일이 없습니다. 모델 평가를 먼저 실행하세요.")
            
            st.markdown("---")
            
            # 4. 동적 변수 통계 요약
            st.subheader("📈 동적 변수 통계 요약")
            
            if len(dynamic_features) > 0:
                stats_data = []
                for feat in dynamic_features:
                    if feat in df_features.columns:
                        series = df_features[feat].dropna()
                        if len(series) > 0:
                            stats_data.append({
                                '변수': feat,
                                '평균': series.mean(),
                                '표준편차': series.std(),
                                '최소값': series.min(),
                                '최대값': series.max(),
                                '유효 데이터': len(series)
                            })
                
                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True)
    
    else:
        st.info("👈 사이드바에서 설정을 선택한 후 '분석 실행' 버튼을 클릭하세요.")

