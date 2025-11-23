#!/usr/bin/env python3
"""
목표 달성을 위한 DB 구조 분석 및 ERD 생성
"""

# 현재 Supabase 테이블 목록
CURRENT_TABLES = {
    "cryptocurrencies": {
        "목적": "암호화폐 기본 정보",
        "상태": "✅ 존재",
        "목표 달성도": "필요 (코인 정보)",
        "주요 컬럼": ["id", "symbol", "name", "market_cap_rank"]
    },
    "whale_address": {
        "목적": "고래 지갑 주소",
        "상태": "✅ 존재",
        "목표 달성도": "필요 (고래 주소)",
        "주요 컬럼": ["id", "chain_type", "address", "name_tag"]
    },
    "whale_transactions": {
        "목적": "고래 거래 기록",
        "상태": "✅ 존재",
        "목표 달성도": "부분적 (매수/매도 구분 필요)",
        "주요 컬럼": ["tx_hash", "from_address", "to_address", "amount", "amount_usd"]
    },
    "internal_transactions": {
        "목적": "내부 거래 (스마트 컨트랙트)",
        "상태": "✅ 존재",
        "목표 달성도": "보조 데이터",
        "주요 컬럼": ["tx_hash", "from_address", "to_address", "value_eth"]
    },
    "influencer": {
        "목적": "인플루언서 포스트",
        "상태": "✅ 존재",
        "목표 달성도": "필요 (감정 분석 포함)",
        "주요 컬럼": ["influencer_id", "platform", "p_coin_name", "p_sentiment_score", "post_date"]
    },
    "market_cap_data": {
        "목적": "시가총액 데이터",
        "상태": "✅ 존재",
        "목표 달성도": "보조 데이터",
        "주요 컬럼": ["crypto_id", "timestamp", "market_cap"]
    },
    "market_data_daily": {
        "목적": "일일 시장 데이터",
        "상태": "✅ 존재",
        "목표 달성도": "보조 데이터",
        "주요 컬럼": ["crypto_id", "date", "open_price", "close_price"]
    },
    "price_history": {
        "목적": "가격 이력",
        "상태": "✅ 존재",
        "목표 달성도": "필요 (가격 변동 분석)",
        "주요 컬럼": ["crypto_id", "timestamp", "open_price", "close_price"]
    },
    "news_sentiment": {
        "목적": "뉴스 감정 분석",
        "상태": "✅ 존재",
        "목표 달성도": "보조 데이터",
        "주요 컬럼": ["crypto_id", "timestamp", "sentiment_score"]
    },
    "reddit_sentiment": {
        "목적": "레딧 감정 분석",
        "상태": "✅ 존재",
        "목표 달성도": "필요 (SNS 감정)",
        "주요 컬럼": ["crypto_id", "timestamp", "sentiment_score"]
    },
    "social_data": {
        "목적": "소셜 미디어 데이터",
        "상태": "✅ 존재",
        "목표 달성도": "필요 (트위터 포함)",
        "주요 컬럼": ["crypto_id", "timestamp", "twitter_followers", "reddit_subscribers"]
    },
    "prediction_accuracy": {
        "목적": "예측 정확도",
        "상태": "✅ 존재",
        "목표 달성도": "보조 데이터",
        "주요 컬럼": ["analyst_id", "symbol", "predicted_price", "actual_price"]
    }
}

# 목표 달성을 위해 추가해야 할 테이블
REQUIRED_TABLES = {
    "whale_transaction_analysis": {
        "목적": "고래별 거래 분석 (매수/매도 구분)",
        "상태": "❌ 없음",
        "필수도": "높음",
        "주요 컬럼": [
            "id (PK)",
            "whale_address_id (FK -> whale_address)",
            "tx_hash (FK -> whale_transactions)",
            "transaction_type (매수/매도)",
            "amount_usd",
            "timestamp",
            "coin_symbol"
        ]
    },
    "price_movement": {
        "목적": "가격 변동 분석 (상승/하락)",
        "상태": "❌ 없음",
        "필수도": "높음",
        "주요 컬럼": [
            "id (PK)",
            "crypto_id (FK -> cryptocurrencies)",
            "timestamp",
            "price_change_percent",
            "movement_type (상승/하락)",
            "time_window (1h, 24h, 7d 등)"
        ]
    },
    "correlation_analysis": {
        "목적": "상관 분석 결과 저장",
        "상태": "❌ 없음",
        "필수도": "높음",
        "주요 컬럼": [
            "id (PK)",
            "crypto_id (FK -> cryptocurrencies)",
            "analysis_date",
            "whale_transaction_correlation",
            "influencer_sentiment_correlation",
            "reddit_sentiment_correlation",
            "twitter_sentiment_correlation",
            "combined_correlation_score"
        ]
    },
    "coin_influence_ranking": {
        "목적": "코인별 영향도 순위 (프론트 표시용)",
        "상태": "❌ 없음",
        "필수도": "높음",
        "주요 컬럼": [
            "id (PK)",
            "crypto_id (FK -> cryptocurrencies)",
            "ranking_date",
            "whale_influence_score",
            "influencer_influence_score",
            "social_influence_score",
            "total_influence_score",
            "rank"
        ]
    },
    "twitter_sentiment": {
        "목적": "트위터 감정 분석 (별도 테이블)",
        "상태": "❌ 없음",
        "필수도": "중간",
        "주요 컬럼": [
            "id (PK)",
            "crypto_id (FK -> cryptocurrencies)",
            "timestamp",
            "tweet_count",
            "sentiment_score",
            "positive_count",
            "negative_count",
            "neutral_count"
        ]
    }
}

def print_analysis():
    print("=" * 80)
    print("📊 목표 달성을 위한 DB 구조 분석")
    print("=" * 80)
    
    print("\n🎯 목표:")
    print("  1. 데이터 수집: 고래 주소 → 거래기록 → 고래별 거래기록")
    print("  2. SNS 포스트: 레딧, 트위터 → 인플루언서의 포스트")
    print("  3. 데이터 분석: 코인 가격(상승/하락) vs 고래 거래(매수/매도) + 인플루언서 감정(긍정/부정)")
    print("  4. 프론트 서비스: 코인별 영향도 순위를 지도에 표시")
    
    print("\n" + "=" * 80)
    print("✅ 현재 존재하는 테이블 (12개)")
    print("=" * 80)
    
    for table_name, info in CURRENT_TABLES.items():
        status = info["상태"]
        purpose = info["목적"]
        achievement = info["목표 달성도"]
        print(f"\n📋 {table_name}")
        print(f"   목적: {purpose}")
        print(f"   상태: {status}")
        print(f"   목표 달성도: {achievement}")
        print(f"   주요 컬럼: {', '.join(info['주요 컬럼'][:3])}...")
    
    print("\n" + "=" * 80)
    print("❌ 추가해야 할 테이블 (5개)")
    print("=" * 80)
    
    for table_name, info in REQUIRED_TABLES.items():
        status = info["상태"]
        purpose = info["목적"]
        required = info["필수도"]
        print(f"\n📋 {table_name}")
        print(f"   목적: {purpose}")
        print(f"   상태: {status}")
        print(f"   필수도: {required}")
        print(f"   주요 컬럼:")
        for col in info["주요 컬럼"]:
            print(f"     - {col}")
    
    print("\n" + "=" * 80)
    print("📈 데이터 흐름 분석")
    print("=" * 80)
    
    print("\n1️⃣ 고래 거래 데이터 흐름:")
    print("   whale_address → whale_transactions → whale_transaction_analysis")
    print("   (고래 주소) → (거래 기록) → (매수/매도 분석)")
    
    print("\n2️⃣ SNS 감정 데이터 흐름:")
    print("   influencer → (감정 분석)")
    print("   reddit_sentiment → (레딧 감정)")
    print("   twitter_sentiment → (트위터 감정)")
    
    print("\n3️⃣ 가격 변동 데이터 흐름:")
    print("   price_history → price_movement")
    print("   (가격 이력) → (상승/하락 분석)")
    
    print("\n4️⃣ 상관 분석 데이터 흐름:")
    print("   whale_transaction_analysis + influencer + price_movement")
    print("   → correlation_analysis → coin_influence_ranking")
    
    print("\n" + "=" * 80)
    print("🔗 주요 관계 (Foreign Keys)")
    print("=" * 80)
    
    relationships = [
        ("whale_transaction_analysis", "whale_address_id", "whale_address", "id"),
        ("whale_transaction_analysis", "tx_hash", "whale_transactions", "tx_hash"),
        ("price_movement", "crypto_id", "cryptocurrencies", "id"),
        ("correlation_analysis", "crypto_id", "cryptocurrencies", "id"),
        ("coin_influence_ranking", "crypto_id", "cryptocurrencies", "id"),
        ("twitter_sentiment", "crypto_id", "cryptocurrencies", "id"),
        ("influencer", "p_coin_name", "cryptocurrencies", "symbol"),  # 간접 관계
        ("whale_transactions", "coin_symbol", "cryptocurrencies", "symbol"),  # 간접 관계
    ]
    
    for child_table, child_col, parent_table, parent_col in relationships:
        print(f"   {child_table}.{child_col} → {parent_table}.{parent_col}")

if __name__ == "__main__":
    print_analysis()



