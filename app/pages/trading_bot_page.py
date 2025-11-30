"""
자동매매 봇 페이지
기존 Streamlit 앱에 통합
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from trading_bot.ui.trading_page import render


def render_page():
    """페이지 렌더링 (기존 페이지와 동일한 인터페이스)"""
    render()

