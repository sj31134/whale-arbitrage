"""
데이터 수집 모듈
기존 프로젝트의 DataLoader, RiskPredictor 등을 래핑하여 사용 (읽기 전용)
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
import pandas as pd

# 기존 프로젝트 모듈 경로 추가
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


class DataCollector:
    """
    데이터 수집 클래스
    기존 프로젝트의 모듈을 래핑하여 사용 (읽기 전용)
    """
    
    def __init__(self, settings: Dict):
        """
        초기화
        
        Args:
            settings: 설정 딕셔너리
        """
        self.settings = settings
        self._data_loader = None
        self._risk_predictor = None
        self._feature_engineer = None
        
        # 지연 초기화 (필요할 때만 로드)
        self._initialized = False
    
    def _init_data_loader(self):
        """DataLoader 초기화 (지연 로드)"""
        if self._data_loader is None:
            try:
                from app.utils.data_loader import DataLoader
                self._data_loader = DataLoader()
                logger.info("DataLoader 초기화 완료")
            except ImportError:
                try:
                    from data_loader import DataLoader
                    self._data_loader = DataLoader()
                    logger.info("DataLoader 초기화 완료 (대체 경로)")
                except ImportError as e:
                    logger.error(f"DataLoader 로드 실패: {e}")
                    raise
    
    def _init_risk_predictor(self):
        """RiskPredictor 초기화 (지연 로드)"""
        if self._risk_predictor is None:
            try:
                from app.utils.risk_predictor import RiskPredictor
                self._risk_predictor = RiskPredictor(model_type="auto")
                logger.info("RiskPredictor 초기화 완료")
            except ImportError:
                try:
                    from risk_predictor import RiskPredictor
                    self._risk_predictor = RiskPredictor(model_type="auto")
                    logger.info("RiskPredictor 초기화 완료 (대체 경로)")
                except ImportError as e:
                    logger.error(f"RiskPredictor 로드 실패: {e}")
                    raise
    
    def _init_feature_engineer(self):
        """FeatureEngineer 초기화 (지연 로드)"""
        if self._feature_engineer is None:
            try:
                sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))
                from feature_engineering import FeatureEngineer
                self._feature_engineer = FeatureEngineer()
                logger.info("FeatureEngineer 초기화 완료")
            except ImportError as e:
                logger.warning(f"FeatureEngineer 로드 실패: {e} (선택적 모듈)")
    
    def get_risk_prediction(self, coin: str = "BTC", date: Optional[str] = None) -> Dict:
        """
        리스크 예측 결과 조회
        
        Args:
            coin: 코인 심볼 ('BTC' 또는 'ETH')
            date: 날짜 (YYYY-MM-DD, None이면 오늘)
        
        Returns:
            {
                'high_volatility_prob': float,
                'risk_score': float,
                'indicators': Dict,
                'success': bool
            }
        """
        try:
            self._init_risk_predictor()
            
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            prediction = self._risk_predictor.predict_risk(date, coin)
            
            if prediction.get('success'):
                data = prediction.get('data', {})
                return {
                    'high_volatility_prob': data.get('high_volatility_prob', 0.5),
                    'risk_score': data.get('risk_score', 50),
                    'indicators': data.get('indicators', {}),
                    'success': True
                }
            else:
                logger.warning(f"리스크 예측 실패: {prediction.get('error')}")
                return {
                    'high_volatility_prob': 0.5,
                    'risk_score': 50,
                    'indicators': {},
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"리스크 예측 조회 실패: {e}")
            return {
                'high_volatility_prob': 0.5,
                'risk_score': 50,
                'indicators': {},
                'success': False
            }
    
    def get_feature_values(self, coin: str = "BTC") -> Dict:
        """
        현재 특성 값들 조회
        
        Args:
            coin: 코인 심볼
        
        Returns:
            특성 값 딕셔너리
        """
        try:
            self._init_data_loader()
            self._init_feature_engineer()
            
            # 최근 데이터 로드
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            df = self._data_loader.load_risk_data(start_date, end_date, coin)
            
            if len(df) == 0:
                logger.warning(f"{coin} 데이터가 없습니다.")
                return {}
            
            # 특성 생성
            if self._feature_engineer:
                df, feature_cols = self._feature_engineer.create_features(df, include_dynamic=True)
            else:
                # FeatureEngineer가 없으면 기본 특성만 사용
                feature_cols = df.columns.tolist()
            
            # 최신 데이터의 특성 값들
            if len(df) > 0:
                latest = df.iloc[-1]
                feature_values = {}
                for col in feature_cols:
                    if col in latest.index and col != 'date':
                        value = latest[col]
                        if pd.notna(value):
                            try:
                                feature_values[col] = float(value)
                            except (ValueError, TypeError):
                                pass
                
                return feature_values
            
            return {}
            
        except Exception as e:
            logger.error(f"특성 값 조회 실패: {e}")
            return {}
    
    def get_current_price(self, coin: str = "BTC") -> float:
        """
        현재가 조회
        
        Args:
            coin: 코인 심볼
        
        Returns:
            현재가 (원)
        """
        try:
            self._init_data_loader()
            
            if coin == "BTC":
                market = "KRW-BTC"
            elif coin == "ETH":
                market = "KRW-ETH"
            else:
                logger.warning(f"지원하지 않는 코인: {coin}")
                return 0.0
            
            # 최신 일봉 데이터 조회
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            df = self._data_loader.load_exchange_data(start_date, end_date, coin)
            
            if len(df) > 0:
                latest = df.iloc[-1]
                price = float(latest['upbit_price'])
                return price
            
            return 0.0
            
        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
            return 0.0
    
    def get_premium_data(self, coin: str = "BTC") -> Dict:
        """
        김치 프리미엄 데이터 조회
        
        Args:
            coin: 코인 심볼
        
        Returns:
            {
                'premium': float,
                'upbit_price': float,
                'binance_price_krw': float,
                'is_negative_premium': bool,
                'is_low_premium': bool
            }
        """
        try:
            self._init_data_loader()
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            df = self._data_loader.load_exchange_data(start_date, end_date, coin)
            
            if len(df) == 0:
                return self._get_default_premium()
            
            latest = df.iloc[-1]
            
            upbit_price = float(latest['upbit_price'])
            binance_price_usd = float(latest['binance_price'])
            krw_usd = float(latest['krw_usd'])
            binance_price_krw = binance_price_usd * krw_usd
            
            if binance_price_krw > 0:
                premium = (upbit_price - binance_price_krw) / binance_price_krw
            else:
                premium = 0.0
            
            negative_threshold = self.settings.get('strategy', {}).get('negative_premium_threshold', -0.01)
            low_threshold = self.settings.get('strategy', {}).get('low_premium_threshold', 0.02)
            
            return {
                'premium': premium,
                'upbit_price': upbit_price,
                'binance_price_usd': binance_price_usd,
                'binance_price_krw': binance_price_krw,
                'is_negative_premium': premium <= negative_threshold,
                'is_low_premium': premium <= low_threshold
            }
            
        except Exception as e:
            logger.error(f"김치 프리미엄 조회 실패: {e}")
            return self._get_default_premium()
    
    def get_whale_data(self, coin: str = "BTC") -> Dict:
        """
        고래 데이터 조회
        
        Args:
            coin: 코인 심볼
        
        Returns:
            {
                'net_flow_usd': float,
                'exchange_inflow_usd': float,
                'exchange_outflow_usd': float
            }
        """
        try:
            self._init_data_loader()
            
            # 최신 고래 데이터 조회 (Supabase 또는 SQLite)
            # 주의: 읽기 전용으로만 사용
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            # SQLite에서 직접 조회 (읽기 전용)
            import sqlite3
            db_path = ROOT / "data" / "project.db"
            
            if db_path.exists():
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                query = f"""
                SELECT 
                    net_flow_usd,
                    exchange_inflow_usd,
                    exchange_outflow_usd
                FROM whale_daily_stats
                WHERE coin_symbol = '{coin}'
                ORDER BY date DESC
                LIMIT 1
                """
                df = pd.read_sql(query, conn)
                conn.close()
                
                if len(df) > 0:
                    return {
                        'net_flow_usd': float(df['net_flow_usd'].iloc[0]) if pd.notna(df['net_flow_usd'].iloc[0]) else 0.0,
                        'exchange_inflow_usd': float(df['exchange_inflow_usd'].iloc[0]) if pd.notna(df['exchange_inflow_usd'].iloc[0]) else 0.0,
                        'exchange_outflow_usd': float(df['exchange_outflow_usd'].iloc[0]) if pd.notna(df['exchange_outflow_usd'].iloc[0]) else 0.0
                    }
            
            return {
                'net_flow_usd': 0.0,
                'exchange_inflow_usd': 0.0,
                'exchange_outflow_usd': 0.0
            }
            
        except Exception as e:
            logger.error(f"고래 데이터 조회 실패: {e}")
            return {
                'net_flow_usd': 0.0,
                'exchange_inflow_usd': 0.0,
                'exchange_outflow_usd': 0.0
            }
    
    def _get_default_premium(self) -> Dict:
        """기본 프리미엄 값"""
        return {
            'premium': 0.0,
            'upbit_price': 0.0,
            'binance_price_usd': 0.0,
            'binance_price_krw': 0.0,
            'is_negative_premium': False,
            'is_low_premium': False
        }

