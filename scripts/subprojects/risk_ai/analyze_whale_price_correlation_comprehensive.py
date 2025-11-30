#!/usr/bin/env python3
"""
고래 데이터 기반 가격 상관성 분석 (종합)
- 독립변수: 고래 구매/판매/이동, 거래소 순유입/유출, 변동성, 파생 선물 거래량
- 종속변수: BTC/ETH 가격 (정적, 변화율, 변동성, 방향)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import logging
from scipy import stats
from sklearn.linear_model import LinearRegression

try:
    from statsmodels.stats.multitest import multipletests
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer
import sqlite3

DB_PATH = ROOT / "data" / "project.db"
OUTPUT_DIR = ROOT / "data" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_whale_data(coin: str = "BTC", start_date: str = "2022-01-01") -> pd.DataFrame:
    """고래 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    # whale_daily_stats 로드
    query_whale = f"""
    SELECT 
        date,
        coin_symbol,
        exchange_inflow_usd,
        exchange_outflow_usd,
        net_flow_usd,
        whale_to_whale_usd,
        active_addresses,
        large_tx_count,
        avg_tx_size_usd
    FROM whale_daily_stats
    WHERE coin_symbol = '{coin}'
    AND date >= '{start_date}'
    ORDER BY date
    """
    
    whale_df = pd.read_sql(query_whale, conn)
    
    # whale_transactions에서 거래 방향별 집계
    query_tx = f"""
    SELECT 
        DATE(block_timestamp) as date,
        coin_symbol,
        transaction_direction,
        SUM(amount_usd) as total_amount_usd,
        COUNT(*) as tx_count
    FROM whale_transactions
    WHERE coin_symbol = '{coin}'
    AND block_timestamp >= '{start_date}'
    GROUP BY DATE(block_timestamp), coin_symbol, transaction_direction
    """
    
    try:
        tx_df = pd.read_sql(query_tx, conn)
        
        # 거래 방향별 피벗
        if not tx_df.empty:
            tx_pivot = tx_df.pivot_table(
                index=['date', 'coin_symbol'],
                columns='transaction_direction',
                values=['total_amount_usd', 'tx_count'],
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # 컬럼명 정리
            tx_pivot.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in tx_pivot.columns]
            
            # whale_df와 병합
            whale_df = pd.merge(
                whale_df,
                tx_pivot,
                on=['date', 'coin_symbol'],
                how='left'
            )
    except Exception as e:
        logging.warning(f"whale_transactions 조회 실패: {e}")
    
    conn.close()
    
    if whale_df.empty:
        return pd.DataFrame()
    
    whale_df['date'] = pd.to_datetime(whale_df['date'])
    
    return whale_df


def load_derivatives_data(coin: str = "BTC", start_date: str = "2022-01-01") -> pd.DataFrame:
    """파생상품 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    symbol = f"{coin}USDT"
    
    query = f"""
    SELECT 
        f.date,
        f.symbol,
        f.avg_funding_rate,
        f.sum_open_interest,
        f.long_short_ratio,
        f.volatility_24h,
        e.taker_buy_sell_ratio,
        e.taker_buy_vol,
        e.taker_sell_vol,
        e.top_trader_long_short_ratio,
        e.bybit_funding_rate,
        e.bybit_oi
    FROM binance_futures_metrics f
    LEFT JOIN futures_extended_metrics e ON f.date = e.date AND f.symbol = e.symbol
    WHERE f.symbol = '{symbol}'
    AND f.date >= '{start_date}'
    ORDER BY f.date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    
    # 숫자 컬럼 변환
    numeric_cols = [
        'avg_funding_rate', 'sum_open_interest', 'long_short_ratio',
        'volatility_24h', 'taker_buy_sell_ratio', 'taker_buy_vol',
        'taker_sell_vol', 'top_trader_long_short_ratio',
        'bybit_funding_rate', 'bybit_oi'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def load_price_data(coin: str = "BTC", start_date: str = "2022-01-01") -> pd.DataFrame:
    """가격 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    symbol = f"{coin}USDT"
    
    query = f"""
    SELECT 
        date,
        close,
        high,
        low,
        volume
    FROM binance_spot_daily
    WHERE symbol = '{symbol}'
    AND date >= '{start_date}'
    ORDER BY date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    
    return df


def calculate_target_variables(price_df: pd.DataFrame) -> pd.DataFrame:
    """종속변수 계산"""
    df = price_df.copy()
    
    # 가격 변화율
    df['price_change_1d'] = df['close'].pct_change(1).shift(-1)  # 다음날 가격 변화율
    df['price_change_7d'] = df['close'].pct_change(7).shift(-7)  # 7일 후 가격 변화율
    df['price_change_30d'] = df['close'].pct_change(30).shift(-30)  # 30일 후 가격 변화율
    
    # 변동성
    df['volatility_1d'] = df['close'].pct_change(1).rolling(window=5).std().shift(-1)
    df['volatility_7d'] = df['close'].pct_change(1).rolling(window=7).std().shift(-7)
    
    # 가격 방향
    df['price_direction_1d'] = (df['close'].diff().shift(-1) > 0).astype(int)
    df['price_direction_7d'] = (df['close'].diff(7).shift(-7) > 0).astype(int)
    
    # 가격 정적 값
    df['price_static'] = df['close']
    
    # 가격 범위
    df['price_range'] = (df['high'] - df['low']) / df['close']
    
    return df


def main():
    parser = argparse.ArgumentParser(description="고래 데이터 기반 가격 상관성 분석 (종합)")
    parser.add_argument("--coin", type=str, default="BTC", help="분석할 코인 심볼 (예: BTC, ETH)")
    parser.add_argument("--start-date", type=str, default="2022-01-01", help="분석 시작일 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    print("=" * 80)
    print("📊 고래 데이터 기반 가격 상관성 분석 (종합)")
    print("=" * 80)
    print(f"코인: {args.coin}")
    print(f"시작일: {args.start_date}")
    
    # 1. 데이터 로드
    print("\n[1/5] 데이터 로드 중...")
    
    price_df = load_price_data(args.coin, args.start_date)
    if price_df.empty:
        logging.error("❌ 가격 데이터를 불러올 수 없습니다.")
        return
    logging.info(f"   ✅ 가격 데이터: {len(price_df)}건")
    
    whale_df = load_whale_data(args.coin, args.start_date)
    if whale_df.empty:
        logging.warning("⚠️ 고래 데이터를 불러올 수 없습니다.")
        whale_df = pd.DataFrame()
    else:
        logging.info(f"   ✅ 고래 데이터: {len(whale_df)}건")
    
    derivatives_df = load_derivatives_data(args.coin, args.start_date)
    if derivatives_df.empty:
        logging.warning("⚠️ 파생상품 데이터를 불러올 수 없습니다.")
        derivatives_df = pd.DataFrame()
    else:
        logging.info(f"   ✅ 파생상품 데이터: {len(derivatives_df)}건")
    
    # 2. 종속변수 계산
    print("\n[2/5] 종속변수 계산 중...")
    price_df = calculate_target_variables(price_df)
    logging.info("   ✅ 종속변수 계산 완료")
    
    # 3. 데이터 병합
    print("\n[3/5] 데이터 병합 중...")
    merged_df = price_df[['date', 'close', 'price_change_1d', 'price_change_7d', 
                          'price_change_30d', 'volatility_1d', 'volatility_7d',
                          'price_direction_1d', 'price_direction_7d', 'price_static', 'price_range']].copy()
    
    if not whale_df.empty:
        merged_df = pd.merge(merged_df, whale_df, on='date', how='inner')
    
    if not derivatives_df.empty:
        merged_df = pd.merge(merged_df, derivatives_df[['date', 'avg_funding_rate', 'sum_open_interest',
                                                         'long_short_ratio', 'volatility_24h',
                                                         'taker_buy_sell_ratio', 'taker_buy_vol',
                                                         'taker_sell_vol', 'top_trader_long_short_ratio',
                                                         'bybit_funding_rate', 'bybit_oi']],
                            on='date', how='inner')
    
    merged_df = merged_df.dropna(subset=['close'])
    
    if merged_df.empty:
        logging.error("❌ 병합된 데이터가 없습니다.")
        return
    
    logging.info(f"   ✅ 병합 완료: {len(merged_df)}건")
    
    # 4. 독립변수 정의
    print("\n[4/5] 상관관계 계산 중...")
    
    # 독립변수 목록
    independent_vars = []
    
    # 고래 거래 데이터
    if not whale_df.empty:
        independent_vars.extend([
            'exchange_inflow_usd',      # 거래소 유입
            'exchange_outflow_usd',     # 거래소 유출
            'net_flow_usd',             # 순유입
            'whale_to_whale_usd',       # 고래간 거래
            'active_addresses',         # 활성 주소 수
            'large_tx_count',           # 대형 거래 건수
            'avg_tx_size_usd'           # 평균 거래 크기
        ])
        
        # 거래 방향별 변수 (있는 경우)
        tx_direction_cols = [col for col in merged_df.columns if 'total_amount_usd' in col or 'tx_count' in col]
        independent_vars.extend(tx_direction_cols)
    
    # 파생상품 데이터
    if not derivatives_df.empty:
        independent_vars.extend([
            'avg_funding_rate',         # 펀딩비
            'sum_open_interest',        # 미결제약정
            'long_short_ratio',        # 롱/숏 비율
            'volatility_24h',          # 변동성
            'taker_buy_sell_ratio',    # Taker 매수/매도 비율
            'taker_buy_vol',           # Taker 매수 거래량
            'taker_sell_vol',          # Taker 매도 거래량
            'top_trader_long_short_ratio',  # 탑 트레이더 롱/숏 비율
            'bybit_funding_rate',      # Bybit 펀딩비
            'bybit_oi'                 # Bybit OI
        ])
    
    # 존재하는 변수만 사용
    available_vars = [v for v in independent_vars if v in merged_df.columns]
    
    # 종속변수 목록
    target_vars = [
        'price_static',           # 현재 가격
        'price_change_1d',        # 1일 후 가격 변화율
        'price_change_7d',        # 7일 후 가격 변화율
        'price_change_30d',       # 30일 후 가격 변화율
        'volatility_1d',          # 1일 후 변동성
        'volatility_7d',          # 7일 후 변동성
        'price_direction_1d',     # 1일 후 가격 방향
        'price_direction_7d',     # 7일 후 가격 방향
        'price_range'             # 가격 범위
    ]
    
    # 5. 상관관계 계산
    correlation_results = []
    
    for var in available_vars:
        for target in target_vars:
            for lag in [0, 1, 3, 7, 14]:  # 0일, 1일, 3일, 7일, 14일 후
                if var in merged_df.columns and target in merged_df.columns:
                    x = merged_df[var].shift(lag).dropna()
                    y = merged_df[target].loc[x.index].dropna()
                    
                    if len(x) > 1 and len(y) > 1 and len(x) == len(y):
                        # NaN 제거
                        valid_mask = ~(pd.isna(x) | pd.isna(y))
                        x_clean = x[valid_mask]
                        y_clean = y[valid_mask]
                        
                        if len(x_clean) > 1:
                            try:
                                pearson_r, pearson_p = stats.pearsonr(x_clean, y_clean)
                                spearman_r, spearman_p = stats.spearmanr(x_clean, y_clean)
                                
                                correlation_results.append({
                                    'variable': var,
                                    'target': target,
                                    'lag': lag,
                                    'pearson_correlation': pearson_r,
                                    'pearson_pvalue': pearson_p,
                                    'spearman_correlation': spearman_r,
                                    'spearman_pvalue': spearman_p,
                                    'sample_size': len(x_clean)
                                })
                            except Exception as e:
                                logging.warning(f"      ⚠️ 상관관계 계산 실패 ({var} vs {target}, lag {lag}): {e}")
    
    if not correlation_results:
        logging.error("❌ 상관관계 결과가 없습니다.")
        return
    
    corr_df = pd.DataFrame(correlation_results)
    
    # FDR 보정
    if HAS_STATSMODELS:
        try:
            pvalues = corr_df['pearson_pvalue'].values
            reject, pvals_corrected, _, _ = multipletests(pvalues, alpha=0.05, method='fdr_bh')
            corr_df['pearson_pvalue_fdr'] = pvals_corrected
            corr_df['is_significant_fdr'] = reject
            logging.info("   ✅ FDR 보정 적용 완료")
        except Exception as e:
            logging.warning(f"   ⚠️ FDR 보정 실패: {e}")
            corr_df['pearson_pvalue_fdr'] = corr_df['pearson_pvalue']
            corr_df['is_significant_fdr'] = corr_df['pearson_pvalue'] < 0.05
    else:
        logging.warning("   ⚠️ statsmodels가 없어 FDR 보정을 건너뜁니다.")
        corr_df['pearson_pvalue_fdr'] = corr_df['pearson_pvalue']
        corr_df['is_significant_fdr'] = corr_df['pearson_pvalue'] < 0.05
    
    # 선형 회귀 분석
    print("\n[5/5] 선형 회귀 분석 중...")
    regression_results = []
    significant_corr_df = corr_df[corr_df['is_significant_fdr']].copy()
    
    if not significant_corr_df.empty:
        for idx, row in significant_corr_df.iterrows():
            var = row['variable']
            target = row['target']
            lag = row['lag']
            
            x = merged_df[var].shift(lag).dropna()
            y = merged_df[target].loc[x.index].dropna()
            
            valid_mask = ~(pd.isna(x) | pd.isna(y))
            x_clean = x[valid_mask]
            y_clean = y[valid_mask]
            
            if len(x_clean) > 1:
                try:
                    model = LinearRegression()
                    model.fit(x_clean.values.reshape(-1, 1), y_clean.values)
                    r_squared = model.score(x_clean.values.reshape(-1, 1), y_clean.values)
                    regression_results.append({
                        'variable': var,
                        'target': target,
                        'lag': lag,
                        'r_squared': r_squared,
                        'coefficient': model.coef_[0],
                        'intercept': model.intercept_
                    })
                except Exception as e:
                    logging.warning(f"      ⚠️ 회귀 분석 실패 ({var} vs {target}, lag {lag}): {e}")
        
        if regression_results:
            reg_df = pd.DataFrame(regression_results)
            corr_df = pd.merge(corr_df, reg_df, on=['variable', 'target', 'lag'], how='left')
            logging.info(f"   ✅ {len(reg_df)}개 회귀 분석 완료")
    
    # 결과 저장
    output_path = OUTPUT_DIR / f"whale_price_correlation_comprehensive_{args.coin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    corr_df.to_csv(output_path, index=False)
    logging.info(f"✅ 결과 저장: {output_path}")
    
    # 요약 출력
    print("\n" + "=" * 80)
    print("📊 상위 20개 유의미한 상관관계")
    print("=" * 80)
    significant = corr_df[corr_df['is_significant_fdr']].sort_values('pearson_correlation', ascending=False, key=abs)
    print(significant.head(20).to_string())
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료")
    print("=" * 80)
    print(f"총 분석 조합: {len(corr_df)}개")
    print(f"유의미한 상관관계: {corr_df['is_significant_fdr'].sum()}개 (p < 0.05, FDR 보정)")
    print("=" * 80)


if __name__ == "__main__":
    main()

