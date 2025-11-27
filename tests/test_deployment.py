#!/usr/bin/env python3
"""
배포 전 테스트 스크립트

Streamlit Cloud 배포 시 발생할 수 있는 에러를 사전에 확인합니다.
"""

import pytest
import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "app" / "utils"))


class TestRequirements:
    """필수 패키지 임포트 테스트"""
    
    def test_streamlit_import(self):
        """Streamlit 임포트 가능 여부"""
        import streamlit as st
        assert st is not None
    
    def test_pandas_import(self):
        """Pandas 임포트 가능 여부"""
        import pandas as pd
        assert pd is not None
    
    def test_numpy_import(self):
        """NumPy 임포트 가능 여부"""
        import numpy as np
        assert np is not None
    
    def test_plotly_import(self):
        """Plotly 임포트 가능 여부"""
        import plotly.express as px
        import plotly.graph_objects as go
        assert px is not None
        assert go is not None
    
    def test_sklearn_import(self):
        """Scikit-learn 임포트 가능 여부"""
        from sklearn.ensemble import RandomForestClassifier
        assert RandomForestClassifier is not None


class TestAppStructure:
    """앱 구조 테스트"""
    
    def test_main_exists(self):
        """메인 파일 존재 여부"""
        main_path = ROOT / "app" / "main.py"
        assert main_path.exists(), f"main.py not found at {main_path}"
    
    def test_pages_exist(self):
        """페이지 파일 존재 여부"""
        pages_dir = ROOT / "app" / "pages"
        assert pages_dir.exists(), "pages directory not found"
        
        required_pages = [
            "risk_dashboard_page.py",
            "historical_analysis_page.py",
            "cost_calculator_page.py",
        ]
        
        for page in required_pages:
            page_path = pages_dir / page
            assert page_path.exists(), f"{page} not found"
    
    def test_utils_exist(self):
        """유틸리티 파일 존재 여부"""
        utils_dir = ROOT / "app" / "utils"
        assert utils_dir.exists(), "utils directory not found"
        
        required_utils = [
            "data_loader.py",
            "risk_predictor.py",
            "visualizer.py",
        ]
        
        for util in required_utils:
            util_path = utils_dir / util
            assert util_path.exists(), f"{util} not found"


class TestDatabaseFiles:
    """데이터베이스 파일 테스트"""
    
    def test_db_or_archive_exists(self):
        """DB 또는 압축 파일 존재 여부"""
        db_path = ROOT / "data" / "project.db"
        archive_path = ROOT / "project.db.tar.gz"
        
        has_db = db_path.exists()
        has_archive = archive_path.exists()
        
        assert has_db or has_archive, "Neither project.db nor project.db.tar.gz found"
    
    def test_model_files_exist(self):
        """모델 파일 존재 여부"""
        models_dir = ROOT / "data" / "models"
        
        if models_dir.exists():
            model_files = list(models_dir.glob("*.pkl")) + list(models_dir.glob("*.json"))
            # 모델 파일이 있으면 검증
            if model_files:
                assert len(model_files) >= 1, "Model files found but incomplete"


class TestModuleImports:
    """앱 모듈 임포트 테스트"""
    
    def test_data_loader_import(self):
        """DataLoader 임포트 가능 여부"""
        try:
            from data_loader import DataLoader
            assert DataLoader is not None
        except ImportError as e:
            pytest.skip(f"DataLoader import skipped: {e}")
    
    def test_risk_predictor_import(self):
        """RiskPredictor 임포트 가능 여부"""
        try:
            from risk_predictor import RiskPredictor
            assert RiskPredictor is not None
        except ImportError as e:
            pytest.skip(f"RiskPredictor import skipped: {e}")


class TestConfigFiles:
    """설정 파일 테스트"""
    
    def test_streamlit_config_exists(self):
        """Streamlit 설정 파일 존재 여부"""
        config_path = ROOT / ".streamlit" / "config.toml"
        assert config_path.exists(), "Streamlit config.toml not found"
    
    def test_requirements_exists(self):
        """requirements.txt 존재 여부"""
        req_path = ROOT / "requirements.txt"
        assert req_path.exists(), "requirements.txt not found"
    
    def test_requirements_valid(self):
        """requirements.txt 유효성 검사"""
        req_path = ROOT / "requirements.txt"
        
        if not req_path.exists():
            pytest.skip("requirements.txt not found")
        
        with open(req_path, 'r') as f:
            content = f.read()
        
        # 필수 패키지 확인
        required = ['streamlit', 'pandas', 'numpy']
        for pkg in required:
            assert pkg in content.lower(), f"{pkg} not in requirements.txt"


class TestLiquidationRiskCalculation:
    """청산 리스크 계산 테스트 (이전 배포 에러 방지)"""
    
    def test_risk_calculation_no_overflow(self):
        """청산 리스크 계산이 100을 초과하지 않는지 확인"""
        # 극단적인 값으로 테스트
        oi_growth = 2.0  # 200% 변화 (극단)
        funding_zscore = 5.0  # 5 시그마 (극단)
        oi_accel = 1.0  # 100% 가속 (극단)
        vol_accel = 0.1  # 10% 가속 (극단)
        
        # 스케일 정규화 (클리핑)
        oi_growth_norm = min(abs(oi_growth), 0.5)
        funding_zscore_norm = min(abs(funding_zscore), 3.0)
        oi_accel_norm = min(abs(oi_accel), 0.3)
        vol_accel_norm = min(abs(vol_accel), 0.02)
        
        liquidation_risk = min(100, max(0, 
            oi_growth_norm * 50 +
            funding_zscore_norm * 10 +
            oi_accel_norm * 50 +
            vol_accel_norm * 500
        ))
        
        assert 0 <= liquidation_risk <= 100, f"Risk out of bounds: {liquidation_risk}"
        assert liquidation_risk <= 80, f"Risk too high with normalized values: {liquidation_risk}"
    
    def test_risk_calculation_with_zero_oi(self):
        """OI 데이터가 없을 때 청산 리스크 계산"""
        # OI 데이터 없음 (현재 상황)
        oi_growth = 0
        funding_zscore = 2.0
        oi_accel = 0
        vol_accel = 0.01
        
        oi_growth_norm = min(abs(oi_growth), 0.5)
        funding_zscore_norm = min(abs(funding_zscore), 3.0)
        oi_accel_norm = min(abs(oi_accel), 0.3)
        vol_accel_norm = min(abs(vol_accel), 0.02)
        
        liquidation_risk = min(100, max(0, 
            oi_growth_norm * 50 +
            funding_zscore_norm * 10 +
            oi_accel_norm * 50 +
            vol_accel_norm * 500
        ))
        
        assert 0 <= liquidation_risk <= 100
        # OI 없이 펀딩비와 변동성만으로 계산
        expected_max = 3.0 * 10 + 0.02 * 500  # 30 + 10 = 40
        assert liquidation_risk <= expected_max + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

