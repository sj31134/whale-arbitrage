#!/usr/bin/env python3
"""
Project 2 UI/UX 서비스 메인 애플리케이션
Streamlit 기반 웹 애플리케이션
"""

import streamlit as st
from pathlib import Path
import sys
import os

# Docker 컨테이너 내부에서는 /app이 루트
if os.path.exists('/app'):
    ROOT = Path('/app')
else:
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
    from app.pages import cost_calculator_page
    cost_calculator_page.render()
elif page == "🎯 최적 전략 추천":
    from app.pages import strategy_recommender_page
    strategy_recommender_page.render()

# 푸터
st.sidebar.markdown("---")
st.sidebar.markdown("**Project 2: Arbitrage Analysis**")
st.sidebar.markdown("데이터 기간: 2024-01-01 ~ 현재")

