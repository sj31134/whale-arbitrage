"""
텔레그램 알림 모듈
"""

import requests
from typing import Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """텔레그램 알림 클래스"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        초기화
        
        Args:
            bot_token: 텔레그램 봇 토큰
            chat_id: 채팅 ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def _send_message(self, message: str) -> bool:
        """
        텔레그램 메시지 전송
        
        Args:
            message: 전송할 메시지
        
        Returns:
            전송 성공 여부
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("텔레그램 설정이 없습니다. 알림을 보낼 수 없습니다.")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 실패: {e}")
            return False
    
    def notify_buy_executed(
        self,
        coin: str,
        price: float,
        quantity: float,
        total_amount: float,
        premium: float,
        whale_signal: Dict,
        k_value: float
    ):
        """매수 체결 알림"""
        message = f"""
🟢 <b>매수 체결</b>

코인: {coin}
체결가: {price:,.0f}원
수량: {quantity:.6f}
총액: {total_amount:,.0f}원

📊 <b>시장 상황</b>
김치 프리미엄: {premium*100:.2f}%
동적 K값: {k_value:.3f}
고래 순매수: {whale_signal.get('net_flow', 0):,.0f} USD

시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self._send_message(message)
    
    def notify_sell_executed(
        self,
        coin: str,
        price: float,
        quantity: float,
        total_amount: float,
        profit_pct: float,
        profit_amount: float,
        premium: float
    ):
        """매도 체결 알림"""
        profit_emoji = "🟢" if profit_pct > 0 else "🔴"
        
        message = f"""
{profit_emoji} <b>매도 체결</b>

코인: {coin}
체결가: {price:,.0f}원
수량: {quantity:.6f}
총액: {total_amount:,.0f}원

💰 <b>수익</b>
수익률: {profit_pct:.2f}%
수익금: {profit_amount:,.0f}원

📊 <b>시장 상황</b>
김치 프리미엄: {premium*100:.2f}%

시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self._send_message(message)
    
    def notify_error(self, error_message: str):
        """에러 알림"""
        message = f"""
❌ <b>에러 발생</b>

{error_message}

시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self._send_message(message)
    
    def notify_status(self, status: str, details: Optional[Dict] = None):
        """상태 알림"""
        message = f"""
ℹ️ <b>봇 상태</b>

{status}
        """.strip()
        
        if details:
            for key, value in details.items():
                message += f"\n{key}: {value}"
        
        message += f"\n\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_message(message)

