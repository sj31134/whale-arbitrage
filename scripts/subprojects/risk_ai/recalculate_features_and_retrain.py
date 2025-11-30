#!/usr/bin/env python3
"""
동적 변수 재계산 및 모델 재학습 스크립트

1. 새로운 데이터로 동적 변수 재계산
2. 피처 데이터 저장
3. 모델 재학습 (XGBoost, LSTM, Hybrid)
4. 모델 성능 평가 및 비교
"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# 프로젝트 모듈 임포트
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

DB_PATH = ROOT / "data" / "project.db"
MODELS_DIR = ROOT / "data" / "models"


def recalculate_features():
    """동적 변수 재계산"""
    logging.info("=" * 80)
    logging.info("동적 변수 재계산 시작")
    logging.info("=" * 80)
    
    engineer = FeatureEngineer()
    
    # 전체 기간 데이터 로드
    logging.info("원본 데이터 로드 중...")
    df = engineer.load_raw_data(start_date="2022-01-01")
    logging.info(f"로드된 데이터: {len(df)}건 ({df['date'].min()} ~ {df['date'].max()})")
    
    # 동적 변수 포함 피처 생성
    logging.info("동적 변수 포함 피처 생성 중...")
    df_features, features = engineer.create_features(df, include_dynamic=True)
    
    logging.info(f"생성된 피처 수: {len(features)}")
    logging.info(f"유효 데이터: {len(df_features)}건")
    
    # 피처 통계 출력
    logging.info("\n피처 통계:")
    logging.info("-" * 80)
    for feature in features[:10]:  # 처음 10개만
        if feature in df_features.columns:
            series = df_features[feature].dropna()
            if len(series) > 0:
                logging.info(f"{feature}: min={series.min():.6f}, max={series.max():.6f}, mean={series.mean():.6f}")
    
    # 동적 변수 통계
    dynamic_features = [f for f in features if any(x in f for x in ['delta', 'accel', 'slope', 'momentum', 'stability'])]
    logging.info(f"\n동적 변수 수: {len(dynamic_features)}")
    
    return df_features, features


def evaluate_feature_quality(df_features, features):
    """피처 품질 평가"""
    logging.info("\n" + "=" * 80)
    logging.info("피처 품질 평가")
    logging.info("=" * 80)
    
    issues = []
    
    # 1. 결측치 확인
    missing = df_features[features].isnull().sum()
    if missing.sum() > 0:
        logging.warning(f"결측치 발견: {missing[missing > 0].to_dict()}")
        issues.append("결측치 존재")
    
    # 2. 무한대 값 확인
    inf_cols = []
    for col in features:
        if col in df_features.columns:
            if np.isinf(df_features[col]).any():
                inf_cols.append(col)
    if inf_cols:
        logging.warning(f"무한대 값 발견: {inf_cols}")
        issues.append("무한대 값 존재")
    
    # 3. 동적 변수 유효성 확인
    dynamic_features = [f for f in features if any(x in f for x in ['delta', 'accel', 'slope'])]
    valid_dynamic = 0
    for feat in dynamic_features:
        if feat in df_features.columns:
            series = df_features[feat].dropna()
            if len(series) > 0 and not np.isinf(series).all():
                valid_dynamic += 1
    
    logging.info(f"유효한 동적 변수: {valid_dynamic}/{len(dynamic_features)}")
    
    if not issues:
        logging.info("✅ 피처 품질 검증 통과")
    else:
        logging.warning(f"⚠️ 피처 품질 이슈: {', '.join(issues)}")
    
    return len(issues) == 0


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    try:
        # 1. 동적 변수 재계산
        df_features, features = recalculate_features()
        
        # 2. 피처 품질 평가
        quality_ok = evaluate_feature_quality(df_features, features)
        
        if not quality_ok:
            logging.warning("피처 품질 이슈가 있어도 계속 진행합니다...")
        
        # 3. 피처 데이터 저장 (선택사항)
        logging.info("\n" + "=" * 80)
        logging.info("피처 데이터 저장")
        logging.info("=" * 80)
        
        features_file = MODELS_DIR / "risk_ai_features_updated.json"
        import json
        feature_data = {
            "features": features,
            "feature_count": len(features),
            "data_count": len(df_features),
            "date_range": {
                "start": str(df_features['date'].min()),
                "end": str(df_features['date'].max())
            },
            "updated_at": datetime.now().isoformat()
        }
        
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(features_file, 'w') as f:
            json.dump(feature_data, f, indent=2)
        
        logging.info(f"피처 메타데이터 저장: {features_file}")
        
        # 4. 모델 재학습 안내
        logging.info("\n" + "=" * 80)
        logging.info("다음 단계: 모델 재학습")
        logging.info("=" * 80)
        logging.info("다음 명령어로 모델을 재학습할 수 있습니다:")
        logging.info("  python scripts/subprojects/risk_ai/train_xgboost_model.py")
        logging.info("  python scripts/subprojects/risk_ai/train_lstm_model.py")
        logging.info("  python scripts/subprojects/risk_ai/train_hybrid_model.py")
        logging.info("  python scripts/subprojects/risk_ai/evaluate_models.py")
        
        logging.info("\n✅ 동적 변수 재계산 완료!")
        
    except Exception as e:
        logging.error(f"오류 발생: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

