"""
기능 2: 최적 전략 추천 페이지
"""

import streamlit as st
from datetime import datetime, date
import sys
from pathlib import Path
import pandas as pd
import os

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
elif os.path.exists('/app'):
    # Docker 컨테이너 내부
    ROOT = Path('/app')
else:
    # 로컬 개발 환경
    ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

from data_loader import DataLoader
from recommender import StrategyRecommender
from visualizer import Visualizer


def render():
    st.header("🎯 최적 전략 추천 (데이트레이딩)")
    st.markdown("특정 날짜에 가장 수익률이 높은 차익거래 방법을 추천합니다.")
    
    # 데이터 로더 초기화
    data_loader = DataLoader()
    recommender = StrategyRecommender()
    
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
    st.sidebar.subheader("📅 날짜 설정")
    
    # 사용 가능한 날짜 목록 가져오기 (선택적)
    if min_date and max_date:
        st.sidebar.caption(f"📅 사용 가능: {min_date} ~ {max_date}")
    
    target_date = st.sidebar.date_input(
        "날짜 선택",
        value=max_date_obj,
        min_value=min_date_obj,
        max_value=max_date_obj,
        help="데이터가 있는 날짜를 선택해주세요. 주말이나 공휴일은 데이터가 없을 수 있습니다."
    )
    
    # 코인 선택
    st.sidebar.subheader("🪙 코인 설정")
    coin = st.sidebar.selectbox("코인", ["BTC", "ETH"], index=0)
    
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
    
    # 추천 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        recommend_button = st.button("🎯 전략 추천", type="primary", use_container_width=True)
    
    if recommend_button:
        # 추천 실행
        with st.spinner("최적 전략 분석 중... 잠시만 기다려주세요."):
            result = recommender.recommend_best_strategy(
                target_date=target_date.strftime("%Y-%m-%d"),
                coin=coin,
                initial_capital=initial_capital
            )
        
        if not result["success"]:
            error_msg = result['error']
            st.error(f"❌ {error_msg}")
            
            # 제안이 있는 경우 (진입 조건 미만족)
            if "suggestion" in result:
                suggestion = result["suggestion"]
                st.warning(f"💡 {suggestion['message']}")
                
                # 제안된 전략 표시
                with st.expander("📊 제안된 전략 (진입 조건 미만족)", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("거래소 쌍", suggestion['pair'])
                        st.metric("Z-Score", f"{suggestion['z_score']:.2f}")
                    with col2:
                        direction_text = "Short Premium" if suggestion['direction'] == 'short_premium' else "Long Premium"
                        st.metric("전략 방향", direction_text)
                        st.metric("프리미엄", f"{suggestion['premium']*100:.2f}%")
                    
                    st.info("⚠️ 이 전략은 진입 조건(Z-Score > 2.5)을 만족하지 않습니다. 더 낮은 임계값을 사용하거나 다른 날짜를 선택해주세요.")
                
                # 모든 거래소 쌍 정보 표시
                if "all_pairs" in result:
                    st.markdown("#### 📊 모든 거래소 쌍 정보")
                    pairs_df = pd.DataFrame(result["all_pairs"])
                    pairs_df['z_score_abs'] = pairs_df['z_score'].abs()
                    pairs_df = pairs_df.sort_values('z_score_abs', ascending=False)
                    pairs_df['premium_pct'] = (pairs_df['premium'] * 100).round(2)
                    pairs_df['meets_criteria'] = pairs_df['z_score_abs'] > 2.5
                    display_df = pairs_df[['pair', 'z_score', 'premium_pct', 'direction', 'meets_criteria']].copy()
                    display_df.columns = ['거래소 쌍', 'Z-Score', '프리미엄 (%)', '방향', '진입 조건 만족']
                    st.dataframe(display_df, use_container_width=True)
            
            # 가장 가까운 날짜 제안이 있는 경우
            if "closest_date" in result:
                closest_date_str = result["closest_date"]
                st.info(f"💡 가장 가까운 날짜 **{closest_date_str}**를 선택하시겠습니까?")
                
                # 가장 가까운 날짜로 자동 재시도 버튼
                if st.button(f"🔄 {closest_date_str}로 재시도", key="retry_closest_date"):
                    st.rerun()
            
            # 사용 가능한 날짜 범위 안내
            if min_date and max_date:
                st.warning(f"📅 사용 가능한 데이터 기간: {min_date} ~ {max_date}")
                st.info("💡 주말이나 공휴일은 데이터가 없을 수 있습니다. 평일 날짜를 선택해주세요.")
            
            return
        
        data = result["data"]
        
        # 추천 결과 표시
        st.success("✅ 최적 전략 추천 완료!")
        st.markdown("---")
        
        # 추천 전략 (큰 카드)
        st.subheader(f"🎯 {target_date} 최적 전략")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### 추천 거래소 쌍: **{data['recommended_pair']}**")
            direction_text = "Short Premium (프리미엄 매도)" if data['direction'] == 'short_premium' else "Long Premium (프리미엄 매수)"
            st.markdown(f"**전략 방향**: {direction_text}")
        
        with col2:
            st.metric(
                "예상 수익률",
                f"{data['expected_return'] * 100:.2f}%",
                delta=f"{data['expected_holding_days']}일 보유"
            )
        
        st.markdown("---")
        
        # 상세 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("현재 프리미엄", f"{data['current_premium'] * 100:.2f}%")
        
        with col2:
            st.metric("Z-Score", f"{data['z_score']:.2f}")
        
        with col3:
            st.metric("예상 보유 기간", f"{data['expected_holding_days']}일")
        
        with col4:
            expected_profit = initial_capital * data['expected_return']
            st.metric("예상 수익금", f"{expected_profit:,.0f} KRW")
        
        st.markdown("---")
        
        # 실행 방법
        st.subheader("📋 실행 방법")
        for step in data['execution_steps']:
            st.markdown(f"- {step}")
        
        st.markdown("---")
        
        # 리스크 정보
        st.subheader("⚠️ 리스크 정보")
        risks = data['risks']
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.info(f"손절매: {risks['stop_loss'] * 100:.1f}%")
        
        with col2:
            st.info(f"최대 보유 기간: {risks['max_holding_days']}일")
        
        with col3:
            st.info(f"수수료: {risks['fee_rate'] * 100:.2f}%")
        
        with col4:
            st.info(f"슬리피지: {risks['slippage'] * 100:.2f}%")
        
        # 대안 전략
        if data['alternatives']:
            st.markdown("---")
            st.subheader("🔄 대안 전략")
            
            for alt in data['alternatives']:
                with st.expander(f"{alt['rank']}순위: {alt['pair']} ({alt['direction']})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("예상 수익률", f"{alt['expected_return'] * 100:.2f}%")
                    with col2:
                        st.metric("Z-Score", f"{alt['z_score']:.2f}")
                    with col3:
                        st.metric("프리미엄", f"{alt['premium'] * 100:.2f}%")
        
        # 프리미엄 타임라인 차트
        st.markdown("---")
        st.subheader("📈 프리미엄 타임라인")
        
        # 전후 30일 데이터 로드
        from datetime import timedelta
        target_dt = datetime.strptime(target_date.strftime("%Y-%m-%d"), "%Y-%m-%d")
        start_date = (target_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = (target_dt + timedelta(days=30)).strftime("%Y-%m-%d")
        
        df = data_loader.load_exchange_data(start_date, end_date, coin)
        
        # 지표 계산
        import sys
        from pathlib import Path
        ROOT = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))
        from backtest_engine_optimized import OptimizedArbitrageBacktest
        backtest = OptimizedArbitrageBacktest(rolling_window=30)
        df = backtest.calculate_indicators(df)
        
        fig = Visualizer.plot_premium_timeline(
            df, 
            data['recommended_pair'],
            target_date.strftime("%Y-%m-%d")
        )
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # 데이터 로더 연결 종료 (페이지가 닫힐 때)
    # data_loader.close()  # Streamlit에서는 세션 유지 필요

