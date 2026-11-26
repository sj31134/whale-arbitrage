"""
UI 모듈
"""


def show_hold(st):
    """Show the project hold even if the optional live trading SDK is absent."""
    from trading_bot import HOLD_MESSAGE

    st.header("자동매매 봇")
    st.info(HOLD_MESSAGE)
    engine = st.session_state.get("bot_engine")
    if engine is not None and engine.is_running:
        st.warning("이 세션에 이전 버전의 봇이 실행 중입니다.")
        if st.button("실행 중인 봇 중지") and engine.stop():
            st.rerun()
