"""
포지션 관리 모듈
현재 포지션 상태 추적 및 수익률 계산
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PositionManager:
    """포지션 관리 클래스"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        초기화
        
        Args:
            data_dir: 데이터 저장 디렉토리 (None이면 기본 경로)
        """
        if data_dir is None:
            base_dir = Path(__file__).resolve().parent.parent
            data_dir = base_dir / "data"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.positions_file = self.data_dir / "positions.json"
        self.current_position = None
        
        # 기존 포지션 로드
        self._load_positions()
    
    def _load_positions(self):
        """포지션 데이터 로드"""
        try:
            if self.positions_file.exists():
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_position = data.get('current_position')
                    logger.info("포지션 데이터 로드 완료")
        except Exception as e:
            logger.warning(f"포지션 데이터 로드 실패: {e}")
            self.current_position = None
    
    def _save_positions(self):
        """포지션 데이터 저장"""
        try:
            data = {
                'current_position': self.current_position,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"포지션 데이터 저장 실패: {e}")
    
    def open_position(
        self, 
        coin: str, 
        quantity: float, 
        entry_price: float,
        market: str
    ) -> bool:
        """
        포지션 진입
        
        Args:
            coin: 코인 심볼
            quantity: 수량
            entry_price: 진입 가격
            market: 마켓 코드
        
        Returns:
            성공 여부
        """
        try:
            if self.current_position is not None:
                logger.warning("이미 포지션이 있습니다. 기존 포지션을 먼저 청산하세요.")
                return False
            
            self.current_position = {
                'coin': coin,
                'quantity': quantity,
                'entry_price': entry_price,
                'entry_time': datetime.now().isoformat(),
                'market': market
            }
            
            self._save_positions()
            logger.info(f"포지션 진입: {coin} {quantity:.6f} @ {entry_price:,.0f}원")
            return True
            
        except Exception as e:
            logger.error(f"포지션 진입 실패: {e}")
            return False
    
    def close_position(self) -> Optional[Dict]:
        """
        포지션 청산
        
        Returns:
            포지션 정보 (없으면 None)
        """
        try:
            if self.current_position is None:
                return None
            
            position = self.current_position.copy()
            self.current_position = None
            self._save_positions()
            
            logger.info(f"포지션 청산: {position['coin']}")
            return position
            
        except Exception as e:
            logger.error(f"포지션 청산 실패: {e}")
            return None
    
    def get_current_position(self) -> Optional[Dict]:
        """현재 포지션 조회"""
        return self.current_position
    
    def calculate_profit(
        self, 
        current_price: float
    ) -> Optional[Dict]:
        """
        수익률 계산
        
        Args:
            current_price: 현재가
        
        Returns:
            {
                'profit_pct': float,  # 수익률 (%)
                'profit_amount': float,  # 수익금 (원)
                'entry_price': float,
                'current_price': float,
                'quantity': float
            }
        """
        if self.current_position is None:
            return None
        
        try:
            entry_price = self.current_position['entry_price']
            quantity = self.current_position['quantity']
            
            profit_pct = (current_price - entry_price) / entry_price
            profit_amount = (current_price - entry_price) * quantity
            
            return {
                'profit_pct': profit_pct,
                'profit_amount': profit_amount,
                'entry_price': entry_price,
                'current_price': current_price,
                'quantity': quantity
            }
            
        except Exception as e:
            logger.error(f"수익률 계산 실패: {e}")
            return None
    
    def has_position(self) -> bool:
        """포지션 보유 여부"""
        return self.current_position is not None

