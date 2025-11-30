"""
데이터 기반 매매 전략
기존 프로젝트의 분석 결과를 활용한 시그널 생성
"""

import json
from pathlib import Path
from typing import Dict, Optional
import logging
import sys

# 프로젝트 루트 경로
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from trading_bot.collectors.data_collector import DataCollector

logger = logging.getLogger(__name__)


class DataDrivenStrategy:
    """
    데이터 기반 매매 전략
    
    기존 프로젝트의 분석 결과 활용:
    1. RiskPredictor의 고변동성 확률 예측
    2. 특성 중요도 기반 가중치 적용
    3. 동적 변수들의 변화율/가속도 활용
    4. 검증된 상관관계 기반 시그널 생성
    """
    
    def __init__(self, settings: Dict, data_collector: DataCollector):
        """
        초기화
        
        Args:
            settings: 설정 딕셔너리
            data_collector: 데이터 수집기 인스턴스
        """
        self.settings = settings
        self.data_collector = data_collector
        
        # 특성 중요도 로드
        self.feature_importance = self._load_feature_importance()
        
        logger.info(f"데이터 기반 전략 초기화 완료 (특성 개수: {len(self.feature_importance)})")
    
    def _load_feature_importance(self) -> Dict:
        """특성 중요도 로드"""
        try:
            metadata_path = ROOT / "data" / "models" / "risk_ai_metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                if 'feature_importance' in metadata:
                    importance = metadata['feature_importance']
                    # 중요도 정규화 (0-1 범위)
                    total = sum(importance.values())
                    if total > 0:
                        normalized = {k: v/total for k, v in importance.items() if v > 0}
                        logger.info(f"특성 중요도 로드 완료: {len(normalized)}개")
                        return normalized
            
            logger.warning("특성 중요도 파일을 찾을 수 없습니다. 기본값을 사용합니다.")
            return {}
            
        except Exception as e:
            logger.warning(f"특성 중요도 로드 실패: {e}")
            return {}
    
    def calculate_buy_signal_score(self, coin: str = "BTC") -> Dict:
        """
        매수 시그널 점수 계산
        
        전략:
        1. 고변동성 확률이 낮을수록 매수 (안정적인 시장)
        2. 특성 중요도 기반 가중치 적용
        3. 동적 변수들의 긍정적 변화 감지
        4. 상관관계 분석 결과 반영
        
        Returns:
            {
                'buy_signal': bool,
                'signal_score': float,  # 0-100 점수
                'components': Dict,  # 각 구성요소별 점수
                'reason': str,
                'high_volatility_prob': float
            }
        """
        try:
            # 1. 리스크 예측 조회
            risk_pred = self.data_collector.get_risk_prediction(coin)
            high_vol_prob = risk_pred['high_volatility_prob']
            
            # 고변동성 확률이 낮을수록 매수 (안정적인 시장)
            # 0.3 이하면 매수 유리, 0.5 이상이면 매수 불리
            volatility_score = max(0, (0.5 - high_vol_prob) * 200)  # 0-100 점수
            
            # 2. 특성 중요도 기반 점수 계산
            feature_score = 0.0
            feature_values = self.data_collector.get_feature_values(coin)
            total_importance = 0.0
            
            for feature, importance in self.feature_importance.items():
                if feature in feature_values:
                    value = feature_values[feature]
                    
                    # 특성별 매수 유리 조건 판단
                    feature_contribution = self._evaluate_feature_for_buy(feature, value, importance)
                    feature_score += feature_contribution
                    total_importance += importance
            
            # 정규화
            if total_importance > 0:
                feature_score = (feature_score / total_importance) * 100
            else:
                feature_score = 50.0  # 중립
            
            # 3. 동적 변수 분석
            dynamic_score = self._evaluate_dynamic_variables(feature_values)
            
            # 4. 종합 점수 계산
            # 가중치: 변동성 40%, 특성 중요도 40%, 동적 변수 20%
            signal_score = (
                volatility_score * 0.4 +
                feature_score * 0.4 +
                dynamic_score * 0.2
            )
            
            # 매수 시그널 임계값: 60점 이상
            buy_signal = signal_score >= 60.0
            
            # 이유 생성
            reasons = []
            if volatility_score > 60:
                reasons.append(f"낮은 변동성 확률 ({high_vol_prob:.2%})")
            if feature_score > 60:
                reasons.append("긍정적 특성 조합")
            if dynamic_score > 60:
                reasons.append("동적 변수 긍정적 변화")
            
            reason = " / ".join(reasons) if reasons else "시그널 약함"
            
            return {
                'buy_signal': buy_signal,
                'signal_score': signal_score,
                'components': {
                    'volatility_score': volatility_score,
                    'feature_score': feature_score,
                    'dynamic_score': dynamic_score
                },
                'reason': reason,
                'high_volatility_prob': high_vol_prob
            }
            
        except Exception as e:
            logger.error(f"매수 시그널 계산 실패: {e}")
            return {
                'buy_signal': False,
                'signal_score': 0.0,
                'components': {},
                'reason': f"에러: {e}",
                'high_volatility_prob': 0.5
            }
    
    def _evaluate_feature_for_buy(self, feature: str, value: float, importance: float) -> float:
        """
        특성별 매수 유리 조건 평가
        
        기존 분석 결과 기반:
        - whale_conc_change_7d: 음수면 매수 유리 (고래 집중도 감소 = 분산)
        - funding_rate_zscore: 음수면 매수 유리 (펀딩비 낮음)
        - volatility_ratio: 낮을수록 매수 유리 (안정적)
        """
        # 특성별 매수 유리 조건
        buy_favorable_conditions = {
            'whale_conc_change_7d': lambda v: -1 if v < 0 else 1,  # 음수면 유리
            'funding_rate_zscore': lambda v: -1 if v < 0 else 1,  # 음수면 유리
            'volatility_ratio': lambda v: 1 if v < 1.0 else -1,  # 1.0 미만이면 유리
            'avg_funding_rate': lambda v: 1 if v < 0.01 else -1,  # 낮을수록 유리
            'net_flow_usd': lambda v: 1 if v > 0 else -1,  # 양수면 유리 (순유입)
            'exchange_outflow_usd': lambda v: 1 if v > 0 else -1,  # 거래소 유출 (매도 압력 감소)
        }
        
        # 기본값: 중립
        direction = 0
        
        for pattern, condition_func in buy_favorable_conditions.items():
            if pattern in feature:
                try:
                    direction = condition_func(value)
                    break
                except Exception:
                    direction = 0
        
        # 중요도 가중치 적용
        return direction * importance * 100
    
    def _evaluate_dynamic_variables(self, feature_values: Dict) -> float:
        """
        동적 변수 평가
        
        동적 변수들의 변화율/가속도가 긍정적이면 매수 유리
        - volatility_delta: 낮을수록 유리 (변동성 감소)
        - oi_delta: 양수면 유리 (OI 증가 = 관심 증가)
        - funding_delta: 음수면 유리 (펀딩비 감소)
        """
        dynamic_features = [
            'volatility_delta', 'oi_delta', 'funding_delta',
            'volatility_accel', 'oi_accel', 'funding_accel',
            'net_flow_delta'
        ]
        
        score = 50.0  # 중립 시작
        count = 0
        
        for feature in dynamic_features:
            if feature in feature_values:
                value = feature_values[feature]
                
                try:
                    # 특성별 평가
                    if 'volatility' in feature:
                        # 변동성 감소는 긍정적
                        contribution = -value * 100
                    elif 'oi' in feature:
                        # OI 증가는 긍정적
                        contribution = value * 50
                    elif 'funding' in feature:
                        # 펀딩비 감소는 긍정적
                        contribution = -value * 200
                    elif 'net_flow' in feature:
                        # 순유입 증가는 긍정적
                        contribution = value * 10
                    else:
                        contribution = 0
                    
                    score += contribution
                    count += 1
                except Exception:
                    pass
        
        # 평균
        if count > 0:
            score = score / count
        
        # 0-100 범위로 제한
        score = max(0, min(100, score))
        
        return score
    
    def calculate_sell_signal_score(self, coin: str = "BTC", entry_price: float = None) -> Dict:
        """
        매도 시그널 점수 계산
        
        전략:
        1. 고변동성 확률이 높을수록 매도 (리스크 회피)
        2. 수익률 기반 익절/손절
        3. 특성 변화 감지
        
        Returns:
            {
                'sell_signal': bool,
                'signal_score': float,
                'reason': str,
                'high_volatility_prob': float,
                'current_price': float,
                'profit_pct': float
            }
        """
        try:
            # 1. 리스크 예측 조회
            risk_pred = self.data_collector.get_risk_prediction(coin)
            high_vol_prob = risk_pred['high_volatility_prob']
            
            # 고변동성 확률이 높을수록 매도 (0.5 이상이면 매도 고려)
            volatility_score = max(0, (high_vol_prob - 0.3) * 200)  # 0-100 점수
            
            # 2. 현재가 조회 (수익률 계산용)
            current_price = self.data_collector.get_current_price(coin)
            
            profit_score = 0.0
            profit_pct = None
            if entry_price and current_price > 0:
                profit_pct = (current_price - entry_price) / entry_price
                
                # 익절/손절 비율 가져오기
                take_profit = self.settings.get('trading', {}).get('take_profit_pct', 0.10)
                stop_loss = self.settings.get('trading', {}).get('stop_loss_pct', -0.05)
                
                # 익절: +10% 이상
                if profit_pct >= take_profit:
                    profit_score = 100.0
                # 손절: -5% 이하
                elif profit_pct <= stop_loss:
                    profit_score = 100.0
                # 중간: 수익률에 비례
                else:
                    profit_score = abs(profit_pct) * 500
            
            # 3. 종합 점수
            signal_score = (
                volatility_score * 0.6 +
                profit_score * 0.4
            )
            
            # 매도 시그널 임계값: 60점 이상
            sell_signal = signal_score >= 60.0
            
            # 이유 생성
            reasons = []
            if high_vol_prob > 0.5:
                reasons.append(f"높은 변동성 확률 ({high_vol_prob:.2%})")
            if entry_price and current_price > 0 and profit_pct is not None:
                if profit_pct >= take_profit:
                    reasons.append(f"익절 ({profit_pct:.2%})")
                elif profit_pct <= stop_loss:
                    reasons.append(f"손절 ({profit_pct:.2%})")
            
            reason = " / ".join(reasons) if reasons else "시그널 약함"
            
            return {
                'sell_signal': sell_signal,
                'signal_score': signal_score,
                'reason': reason,
                'high_volatility_prob': high_vol_prob,
                'current_price': current_price,
                'profit_pct': profit_pct
            }
            
        except Exception as e:
            logger.error(f"매도 시그널 계산 실패: {e}")
            return {
                'sell_signal': False,
                'signal_score': 0.0,
                'reason': f"에러: {e}",
                'high_volatility_prob': 0.5,
                'current_price': 0.0,
                'profit_pct': None
            }

