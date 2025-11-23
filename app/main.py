#!/usr/bin/env python3
"""
Project 2 UI/UX 서비스 메인 애플리케이션
Streamlit 기반 웹 애플리케이션
"""

import streamlit as st
from pathlib import Path
import sys
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

# 페이지 설정
st.set_page_config(
    page_title="차익거래 분석 서비스",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 메인 타이틀
st.title("💰 차익거래 분석 서비스")
st.markdown("---")

# 사이드바
st.sidebar.title("📋 메뉴")
page = st.sidebar.selectbox(
    "페이지 선택",
    [
        "📊 차익거래 비용 계산기",
        "🎯 최적 전략 추천"
    ]
)

# 페이지 라우팅
if page == "📊 차익거래 비용 계산기":
    # Streamlit Cloud 경로 처리
    try:
        from app.pages import cost_calculator_page
    except ImportError:
        from pages import cost_calculator_page
    cost_calculator_page.render()
elif page == "🎯 최적 전략 추천":
    # Streamlit Cloud 경로 처리
    try:
        from app.pages import strategy_recommender_page
    except ImportError:
        from pages import strategy_recommender_page
    strategy_recommender_page.render()

# 푸터
st.sidebar.markdown("---")
st.sidebar.markdown("**Project 2: Arbitrage Analysis**")
st.sidebar.markdown("데이터 기간: 2024-01-01 ~ 현재")

