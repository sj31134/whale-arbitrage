"""
자동매매 봇 엔진 코어
메인 루프 실행 및 시그널 생성/주문 실행 통합
"""

import threading
import time
from typing import Dict, Optional
from datetime import datetime
import logging

from trading_bot.collectors.data_collector import DataCollector
from trading_bot.collectors.market_data import MarketDataCollector
from trading_bot.strategies.data_driven_strategy import DataDrivenStrategy
from trading_bot.strategies.premium_filter import PremiumFilter
from trading_bot.execution.order_executor import OrderExecutor
from trading_bot.execution.balance_manager import BalanceManager
from trading_bot.core.position_manager import PositionManager
from trading_bot.utils.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


class TradingBotEngine:
    """자동매매 봇 엔진"""
    
    def __init__(self, settings: Dict):
        """
        초기화
        
        Args:
            settings: 설정 딕셔너리
        """
        self.settings = settings
        self.is_running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        # 모듈 초기화
        self.data_collector = DataCollector(settings)
        self.market_data = MarketDataCollector(
            settings.get('api', {}).get('upbit_access_key', ''),
            settings.get('api', {}).get('upbit_secret_key', '')
        )
        self.strategy = DataDrivenStrategy(settings, self.data_collector)
        self.premium_filter = PremiumFilter(settings, self.data_collector)
        self.order_executor = OrderExecutor(
            settings.get('api', {}).get('upbit_access_key', ''),
            settings.get('api', {}).get('upbit_secret_key', '')
        )
        self.balance_manager = BalanceManager(self.market_data)
        self.position_manager = PositionManager()
        
        # 알림 설정
        telegram_settings = settings.get('telegram', {})
        if telegram_settings.get('bot_token') and telegram_settings.get('chat_id'):
            self.notifier = TelegramNotifier(
                telegram_settings['bot_token'],
                telegram_settings['chat_id']
            )
        else:
            self.notifier = None
            logger.warning("텔레그램 알림이 설정되지 않았습니다.")
        
        # 거래 설정
        trading_settings = settings.get('trading', {})
        self.target_coin = trading_settings.get('target_coin', 'BTC')
        self.market = f"KRW-{self.target_coin}"
        self.initial_capital = trading_settings.get('initial_capital', 1000000)
        self.max_position_size = trading_settings.get('max_position_size', 0.3)
        
        # 체크 간격
        risk_settings = settings.get('risk_management', {})
        self.check_interval = risk_settings.get('check_interval', 60)
        
        logger.info("봇 엔진 초기화 완료")
    
    def start(self) -> bool:
        """
        봇 시작
        
        Returns:
            시작 성공 여부
        """
        if self.is_running:
            logger.warning("봇이 이미 실행 중입니다.")
            return False
        
        try:
            # API 연결 확인
            if not self.order_executor.is_connected():
                logger.error("업비트 API 연결 실패. 설정을 확인하세요.")
                return False
            
            self.is_running = True
            self._stop_event.clear()
            
            # 백그라운드 스레드 시작
            self._thread = threading.Thread(target=self._main_loop, daemon=True)
            self._thread.start()
            
            logger.info("봇 시작 완료")
            
            if self.notifier:
                self.notifier.notify_status("봇이 시작되었습니다.")
            
            return True
            
        except Exception as e:
            logger.error(f"봇 시작 실패: {e}")
            self.is_running = False
            return False
    
    def stop(self) -> bool:
        """
        봇 중지
        
        Returns:
            중지 성공 여부
        """
        if not self.is_running:
            logger.warning("봇이 실행 중이 아닙니다.")
            return False
        
        try:
            self.is_running = False
            self._stop_event.set()
            
            if self._thread:
                self._thread.join(timeout=5)
            
            logger.info("봇 중지 완료")
            
            if self.notifier:
                self.notifier.notify_status("봇이 중지되었습니다.")
            
            return True
            
        except Exception as e:
            logger.error(f"봇 중지 실패: {e}")
            return False
    
    def _main_loop(self):
        """메인 루프"""
        logger.info("=" * 80)
        logger.info("자동매매 봇 메인 루프 시작")
        logger.info(f"대상 코인: {self.target_coin}")
        logger.info(f"체크 간격: {self.check_interval}초")
        logger.info("=" * 80)
        
        while self.is_running and not self._stop_event.is_set():
            try:
                self._check_and_execute()
                
                # 대기 (체크 간격)
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"메인 루프 오류: {e}")
                if self.notifier:
                    self.notifier.notify_error(f"메인 루프 오류: {e}")
                time.sleep(self.check_interval)
        
        logger.info("메인 루프 종료")
    
    def _check_and_execute(self):
        """시그널 확인 및 주문 실행"""
        try:
            # 현재 포지션 확인
            current_position = self.position_manager.get_current_position()
            
            if current_position is None:
                # 포지션이 없으면 매수 검토
                self._check_buy_signal()
            else:
                # 포지션이 있으면 매도 검토
                self._check_sell_signal(current_position)
                
        except Exception as e:
            logger.error(f"시그널 확인 실패: {e}")
    
    def _check_buy_signal(self):
        """매수 시그널 확인 및 실행"""
        try:
            # 1. 프리미엄 필터 확인
            if not self.premium_filter.should_allow_buy(self.target_coin):
                logger.debug("매수 차단: 김치 프리미엄 필터")
                return
            
            # 2. 데이터 기반 매수 시그널 확인
            buy_signal = self.strategy.calculate_buy_signal_score(self.target_coin)
            
            if not buy_signal['buy_signal']:
                logger.debug(f"매수 차단: {buy_signal['reason']}")
                return
            
            # 3. 현재가 조회
            current_price = self.data_collector.get_current_price(self.target_coin)
            if current_price <= 0:
                logger.warning("현재가 조회 실패")
                return
            
            # 4. 포지션 크기 계산
            krw_balance = self.balance_manager.get_balance("KRW")
            if krw_balance <= 0:
                logger.warning("원화 잔고가 없습니다.")
                return
            
            multiplier = self.premium_filter.get_position_size_multiplier(self.target_coin)
            position_size = self.balance_manager.calculate_position_size(
                krw_balance,
                self.max_position_size,
                current_price,
                multiplier
            )
            
            quantity = self.balance_manager.calculate_quantity(position_size, current_price)
            
            if quantity <= 0:
                logger.warning("주문 수량이 0입니다.")
                return
            
            # 5. 매수 주문 실행
            logger.info(f"매수 시그널 발생: {buy_signal['reason']} (점수: {buy_signal['signal_score']:.1f})")
            order_result = self.order_executor.place_buy_order(
                self.market,
                quantity=quantity,
                order_type="market"
            )
            
            if order_result['success']:
                # 포지션 기록
                self.position_manager.open_position(
                    self.target_coin,
                    quantity,
                    current_price,
                    self.market
                )
                
                # 알림 전송
                if self.notifier:
                    premium_data = self.premium_filter.get_premium_info(self.target_coin)
                    whale_data = self.data_collector.get_whale_data(self.target_coin)
                    self.notifier.notify_buy_executed(
                        coin=self.target_coin,
                        price=current_price,
                        quantity=quantity,
                        total_amount=position_size,
                        premium=premium_data['premium'],
                        whale_signal={'net_flow': whale_data['net_flow_usd']},
                        k_value=0.5  # TODO: 동적 K값 계산 추가
                    )
                
                logger.info(f"매수 체결: {self.target_coin} {quantity:.6f} @ {current_price:,.0f}원")
            else:
                logger.error(f"매수 주문 실패: {order_result.get('error')}")
                if self.notifier:
                    self.notifier.notify_error(f"매수 주문 실패: {order_result.get('error')}")
                
        except Exception as e:
            logger.error(f"매수 시그널 확인 실패: {e}")
            if self.notifier:
                self.notifier.notify_error(f"매수 시그널 확인 실패: {e}")
    
    def _check_sell_signal(self, position: Dict):
        """매도 시그널 확인 및 실행"""
        try:
            entry_price = position['entry_price']
            
            # 매도 시그널 확인
            sell_signal = self.strategy.calculate_sell_signal_score(
                self.target_coin,
                entry_price
            )
            
            if not sell_signal['sell_signal']:
                logger.debug(f"매도 차단: {sell_signal['reason']}")
                return
            
            # 현재가 조회
            current_price = sell_signal.get('current_price', 0)
            if current_price <= 0:
                current_price = self.data_collector.get_current_price(self.target_coin)
            
            if current_price <= 0:
                logger.warning("현재가 조회 실패")
                return
            
            # 매도 주문 실행
            quantity = position['quantity']
            logger.info(f"매도 시그널 발생: {sell_signal['reason']} (점수: {sell_signal['signal_score']:.1f})")
            
            order_result = self.order_executor.place_sell_order(
                self.market,
                quantity=quantity,
                order_type="market"
            )
            
            if order_result['success']:
                # 포지션 청산
                closed_position = self.position_manager.close_position()
                
                # 수익 계산
                profit_pct = sell_signal.get('profit_pct', 0) * 100
                profit_amount = (current_price - entry_price) * quantity
                
                # 알림 전송
                if self.notifier:
                    premium_data = self.premium_filter.get_premium_info(self.target_coin)
                    self.notifier.notify_sell_executed(
                        coin=self.target_coin,
                        price=current_price,
                        quantity=quantity,
                        total_amount=current_price * quantity,
                        profit_pct=profit_pct,
                        profit_amount=profit_amount,
                        premium=premium_data['premium']
                    )
                
                logger.info(f"매도 체결: {self.target_coin} {quantity:.6f} @ {current_price:,.0f}원 (수익: {profit_pct:.2f}%)")
            else:
                logger.error(f"매도 주문 실패: {order_result.get('error')}")
                if self.notifier:
                    self.notifier.notify_error(f"매도 주문 실패: {order_result.get('error')}")
                
        except Exception as e:
            logger.error(f"매도 시그널 확인 실패: {e}")
            if self.notifier:
                self.notifier.notify_error(f"매도 시그널 확인 실패: {e}")
    
    def get_status(self) -> Dict:
        """
        봇 상태 조회
        
        Returns:
            {
                'is_running': bool,
                'current_position': Dict,
                'balance': Dict,
                'last_check': str
            }
        """
        position = self.position_manager.get_current_position()
        balances = self.balance_manager.get_all_balances()
        
        return {
            'is_running': self.is_running,
            'current_position': position,
            'balance': balances,
            'last_check': datetime.now().isoformat()
        }

