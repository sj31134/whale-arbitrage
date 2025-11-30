"""
자동매매 봇 Streamlit UI 페이지
"""

import streamlit as st
from pathlib import Path
import sys
from typing import Dict, Optional
import json
import pandas as pd

# 프로젝트 루트 경로
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from trading_bot.config.settings_manager import SettingsManager
from trading_bot.core.bot_engine import TradingBotEngine
from trading_bot.utils.validators import (
    validate_api_key, validate_number, validate_required, validate_coin_symbol
)
from trading_bot.utils.logger import setup_logger

# 로거 설정
logger = setup_logger("trading_bot_ui")


def render():
    """UI 렌더링"""
    st.header("🤖 자동매매 봇")
    st.markdown("기존 프로젝트의 분석 결과를 활용한 데이터 기반 자동매매 시스템")
    
    # 설정 관리자 초기화
    settings_manager = SettingsManager()
    
    # 세션 상태 초기화
    if 'bot_engine' not in st.session_state:
        st.session_state.bot_engine = None
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["⚙️ 설정", "📊 모니터링", "🎮 제어"])
    
    with tab1:
        render_settings_tab(settings_manager)
    
    with tab2:
        render_monitoring_tab()
    
    with tab3:
        render_control_tab(settings_manager)


def render_settings_tab(settings_manager: SettingsManager):
    """설정 탭"""
    st.subheader("⚙️ 설정")
    
    # 기존 설정 로드
    current_settings = settings_manager.load_settings()
    
    with st.form("settings_form"):
        st.markdown("### API 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            upbit_access_key = st.text_input(
                "업비트 Access Key",
                value=current_settings.get('api', {}).get('upbit_access_key', ''),
                type="password",
                help="업비트 Open API에서 발급받은 Access Key"
            )
        
        with col2:
            upbit_secret_key = st.text_input(
                "업비트 Secret Key",
                value=current_settings.get('api', {}).get('upbit_secret_key', ''),
                type="password",
                help="업비트 Open API에서 발급받은 Secret Key"
            )
        
        st.markdown("### 텔레그램 알림 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            telegram_bot_token = st.text_input(
                "텔레그램 봇 토큰",
                value=current_settings.get('telegram', {}).get('bot_token', ''),
                type="password",
                help="@BotFather에서 발급받은 봇 토큰"
            )
        
        with col2:
            telegram_chat_id = st.text_input(
                "텔레그램 채팅 ID",
                value=current_settings.get('telegram', {}).get('chat_id', ''),
                help="@userinfobot으로 조회 가능"
            )
        
        st.markdown("### 거래 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            target_coin = st.selectbox(
                "대상 코인",
                options=["BTC", "ETH"],
                index=0 if current_settings.get('trading', {}).get('target_coin', 'BTC') == 'BTC' else 1
            )
            
            initial_capital = st.number_input(
                "초기 자본금 (원)",
                min_value=100000,
                value=int(current_settings.get('trading', {}).get('initial_capital', 1000000)),
                step=100000
            )
        
        with col2:
            max_position_size = st.slider(
                "최대 포지션 비율",
                min_value=0.1,
                max_value=0.5,
                value=float(current_settings.get('trading', {}).get('max_position_size', 0.3)),
                step=0.05,
                help="자본금 대비 최대 포지션 비율"
            )
            
            stop_loss_pct = st.number_input(
                "손절매 비율 (%)",
                min_value=-10.0,
                max_value=0.0,
                value=float(current_settings.get('trading', {}).get('stop_loss_pct', -0.05)) * 100,
                step=0.5
            )
        
        take_profit_pct = st.number_input(
            "익절 비율 (%)",
            min_value=0.0,
            max_value=50.0,
            value=float(current_settings.get('trading', {}).get('take_profit_pct', 0.10)) * 100,
            step=1.0
        )
        
        st.markdown("### 전략 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            volatility_window = st.number_input(
                "변동성 윈도우 (일)",
                min_value=3,
                max_value=10,
                value=int(current_settings.get('strategy', {}).get('volatility_window', 5)),
                step=1
            )
        
        with col2:
            check_interval = st.number_input(
                "체크 간격 (초)",
                min_value=30,
                max_value=300,
                value=int(current_settings.get('risk_management', {}).get('check_interval', 60)),
                step=10
            )
        
        # 저장 버튼
        submitted = st.form_submit_button("💾 설정 저장", use_container_width=True)
        
        if submitted:
            # 입력 검증
            errors = []
            
            if upbit_access_key:
                is_valid, error = validate_api_key(upbit_access_key)
                if not is_valid:
                    errors.append(f"업비트 Access Key: {error}")
            
            if upbit_secret_key:
                is_valid, error = validate_api_key(upbit_secret_key)
                if not is_valid:
                    errors.append(f"업비트 Secret Key: {error}")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # 설정 저장
                new_settings = {
                    'api': {
                        'upbit_access_key': upbit_access_key,
                        'upbit_secret_key': upbit_secret_key,
                        'binance_api_key': current_settings.get('api', {}).get('binance_api_key', ''),
                        'binance_secret_key': current_settings.get('api', {}).get('binance_secret_key', '')
                    },
                    'telegram': {
                        'bot_token': telegram_bot_token,
                        'chat_id': telegram_chat_id
                    },
                    'database': current_settings.get('database', {}),
                    'trading': {
                        'target_coin': target_coin,
                        'initial_capital': initial_capital,
                        'max_position_size': max_position_size,
                        'stop_loss_pct': stop_loss_pct / 100,
                        'take_profit_pct': take_profit_pct / 100
                    },
                    'strategy': {
                        'volatility_window': volatility_window,
                        'negative_premium_threshold': current_settings.get('strategy', {}).get('negative_premium_threshold', -0.01),
                        'low_premium_threshold': current_settings.get('strategy', {}).get('low_premium_threshold', 0.02),
                        'whale_lookback_hours': current_settings.get('strategy', {}).get('whale_lookback_hours', 1),
                        'whale_buy_threshold': current_settings.get('strategy', {}).get('whale_buy_threshold', 0.0)
                    },
                    'risk_management': {
                        'max_retries': current_settings.get('risk_management', {}).get('max_retries', 3),
                        'retry_delay': current_settings.get('risk_management', {}).get('retry_delay', 5),
                        'check_interval': check_interval
                    }
                }
                
                if settings_manager.save_settings(new_settings):
                    st.success("✅ 설정이 저장되었습니다.")
                    st.rerun()
                else:
                    st.error("❌ 설정 저장에 실패했습니다.")


def render_monitoring_tab():
    """모니터링 탭"""
    st.subheader("📊 모니터링")
    
    if st.session_state.bot_engine is None:
        st.info("봇이 시작되지 않았습니다. '제어' 탭에서 봇을 시작하세요.")
        return
    
    try:
        status = st.session_state.bot_engine.get_status()
        
        # 상태 정보
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_emoji = "🟢" if status['is_running'] else "🔴"
            st.metric("봇 상태", f"{status_emoji} {'실행 중' if status['is_running'] else '중지됨'}")
        
        with col2:
            position = status.get('current_position')
            if position:
                st.metric("현재 포지션", f"{position['coin']} {position['quantity']:.6f}")
            else:
                st.metric("현재 포지션", "없음")
        
        with col3:
            balance = status.get('balance', {})
            krw_balance = balance.get('KRW', 0)
            st.metric("원화 잔고", f"{krw_balance:,.0f}원")
        
        # 포지션 상세 정보
        if position:
            st.markdown("### 포지션 상세")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("진입 가격", f"{position['entry_price']:,.0f}원")
            
            with col2:
                from datetime import datetime
                entry_time = datetime.fromisoformat(position['entry_time'])
                st.metric("진입 시간", entry_time.strftime("%Y-%m-%d %H:%M:%S"))
            
            with col3:
                # 현재가 조회
                from trading_bot.collectors.data_collector import DataCollector
                data_collector = DataCollector(st.session_state.bot_engine.settings)
                current_price = data_collector.get_current_price(position['coin'])
                st.metric("현재가", f"{current_price:,.0f}원")
            
            with col4:
                if current_price > 0:
                    profit_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    profit_amount = (current_price - position['entry_price']) * position['quantity']
                    st.metric("수익률", f"{profit_pct:.2f}%", delta=f"{profit_amount:,.0f}원")
        
        # 잔고 정보
        st.markdown("### 잔고 정보")
        if balance:
            balance_df = pd.DataFrame(list(balance.items()), columns=['통화', '잔고'])
            st.dataframe(balance_df, use_container_width=True, hide_index=True)
        else:
            st.info("잔고 정보가 없습니다.")
        
    except Exception as e:
        st.error(f"모니터링 정보 조회 실패: {e}")
        logger.error(f"모니터링 정보 조회 실패: {e}")


def render_control_tab(settings_manager: SettingsManager):
    """제어 탭"""
    st.subheader("🎮 제어")
    
    # 설정 확인
    settings = settings_manager.load_settings()
    api_key = settings.get('api', {}).get('upbit_access_key', '')
    
    if not api_key:
        st.warning("⚠️ 먼저 '설정' 탭에서 API 키를 입력하세요.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 봇 시작", use_container_width=True, type="primary"):
            try:
                if st.session_state.bot_engine is None:
                    # 봇 엔진 생성
                    st.session_state.bot_engine = TradingBotEngine(settings)
                
                if st.session_state.bot_engine.start():
                    st.success("✅ 봇이 시작되었습니다.")
                    st.rerun()
                else:
                    st.error("❌ 봇 시작에 실패했습니다. 설정을 확인하세요.")
            except Exception as e:
                st.error(f"❌ 봇 시작 실패: {e}")
                logger.error(f"봇 시작 실패: {e}")
    
    with col2:
        if st.button("⏹️ 봇 중지", use_container_width=True):
            try:
                if st.session_state.bot_engine:
                    if st.session_state.bot_engine.stop():
                        st.success("✅ 봇이 중지되었습니다.")
                        st.rerun()
                    else:
                        st.error("❌ 봇 중지에 실패했습니다.")
                else:
                    st.warning("⚠️ 봇이 실행 중이 아닙니다.")
            except Exception as e:
                st.error(f"❌ 봇 중지 실패: {e}")
                logger.error(f"봇 중지 실패: {e}")
    
    # 상태 표시
    if st.session_state.bot_engine:
        status = st.session_state.bot_engine.get_status()
        
        st.markdown("### 봇 상태")
        if status['is_running']:
            st.success("🟢 봇이 실행 중입니다.")
        else:
            st.info("🔴 봇이 중지되었습니다.")
        
        st.json(status)

