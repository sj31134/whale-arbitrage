"""
자동매매 봇 페이지
기존 Streamlit 앱에 통합
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def render_page():
    """페이지 렌더링 (기존 페이지와 동일한 인터페이스)"""
    from trading_bot import LIVE_TRADING_ON_HOLD
    if LIVE_TRADING_ON_HOLD:
        import streamlit as st
        from trading_bot.ui import show_hold
        show_hold(st)
        return

    try:
        # 필수 패키지 확인
        try:
            import pyupbit
        except ImportError:
            import streamlit as st
            st.error("❌ 자동매매 봇 모듈을 불러올 수 없습니다.")
            st.info("💡 `pyupbit` 패키지가 설치되지 않았습니다.")
            st.code("pip install pyupbit")
            st.warning("⚠️ 이 기능은 추가 패키지 설치가 필요합니다.")
            return
        
        # trading_bot 모듈 import
        from trading_bot.ui.trading_page import render
        render()
    except ImportError as e:
        import streamlit as st
        st.error("❌ 자동매매 봇 모듈을 불러올 수 없습니다.")
        st.info("💡 필요한 패키지가 설치되지 않았을 수 있습니다.")
        st.code(f"오류: {str(e)}")
        st.warning("⚠️ 이 기능은 추가 패키지 설치가 필요합니다.")
    except Exception as e:
        import streamlit as st
        st.error("❌ 자동매매 봇 실행 중 오류가 발생했습니다.")
        st.code(f"오류: {str(e)}")

