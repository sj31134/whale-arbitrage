#!/usr/bin/env python3
"""
Open Interest 과거 데이터 수집 대체 방법 연구
- Coinglass API
- 다른 데이터 소스
- 대체 지표 사용
"""

import requests
import json
from pathlib import Path

def test_coinglass_api():
    """Coinglass API 테스트"""
    print("=" * 80)
    print("🔍 Coinglass API 테스트")
    print("=" * 80)
    
    # Coinglass Open Interest API (예상)
    # 실제 API 엔드포인트는 문서 확인 필요
    url = "https://open-api.coinglass.com/public/v2/open_interest"
    
    try:
        # API 키가 필요할 수 있음
        headers = {
            "accept": "application/json"
        }
        params = {
            "symbol": "BTC",
            "interval": "1d"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 응답 성공")
            return True
        else:
            print(f"⚠️ API 응답 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return False

def research_alternative_sources():
    """대체 데이터 소스 연구"""
    print("\n" + "=" * 80)
    print("📚 Open Interest 데이터 대체 소스 연구")
    print("=" * 80)
    
    alternatives = [
        {
            "name": "Coinglass",
            "url": "https://www.coinglass.com/",
            "api": "https://open-api.coinglass.com/",
            "free_tier": "제한적",
            "historical_data": "제한적",
            "note": "무료 API는 제한적일 수 있음"
        },
        {
            "name": "CryptoQuant",
            "url": "https://cryptoquant.com/",
            "api": "https://api.cryptoquant.com/",
            "free_tier": "제한적",
            "historical_data": "유료",
            "note": "무료 API는 제한적, 유료 플랜 필요"
        },
        {
            "name": "Glassnode",
            "url": "https://glassnode.com/",
            "api": "https://api.glassnode.com/",
            "free_tier": "제한적",
            "historical_data": "유료",
            "note": "무료 API는 제한적, 유료 플랜 필요"
        },
        {
            "name": "Binance 24hr Ticker (대체 지표)",
            "url": "Binance API",
            "api": "/fapi/v1/ticker/24hr",
            "free_tier": "무료",
            "historical_data": "실시간만",
            "note": "과거 데이터 없음, 실시간만 가능"
        },
        {
            "name": "거래량 기반 추정",
            "url": "N/A",
            "api": "N/A",
            "free_tier": "무료",
            "historical_data": "가능",
            "note": "거래량과 OI의 상관관계를 이용한 추정 (정확도 낮음)"
        }
    ]
    
    print("\n대체 데이터 소스 목록:")
    for i, alt in enumerate(alternatives, 1):
        print(f"\n{i}. {alt['name']}")
        print(f"   URL: {alt['url']}")
        print(f"   API: {alt['api']}")
        print(f"   무료 티어: {alt['free_tier']}")
        print(f"   과거 데이터: {alt['historical_data']}")
        print(f"   참고: {alt['note']}")
    
    return alternatives

def suggest_solutions():
    """해결 방안 제시"""
    print("\n" + "=" * 80)
    print("💡 해결 방안")
    print("=" * 80)
    
    solutions = [
        {
            "방안": "1. 매일 자동 수집 (권장)",
            "설명": "Binance API로 최근 30일 데이터를 매일 수집하여 축적",
            "장점": "무료, 자동화 가능, 시간이 지나면 데이터 축적",
            "단점": "과거 데이터는 수집 불가, 시간이 오래 걸림",
            "구현": "cron job 또는 스케줄러로 매일 실행"
        },
        {
            "방안": "2. 유료 API 사용",
            "설명": "CryptoQuant, Glassnode 등 유료 API 사용",
            "장점": "과거 데이터 즉시 확보 가능",
            "단점": "비용 발생",
            "구현": "API 키 발급 후 스크립트 작성"
        },
        {
            "방안": "3. 대체 지표 사용",
            "설명": "OI 대신 거래량, 펀딩비 등 다른 지표 활용",
            "장점": "즉시 사용 가능",
            "단점": "OI 특유의 정보 손실",
            "구현": "Feature Engineering 수정"
        },
        {
            "방안": "4. OI 특성 제거",
            "설명": "OI 관련 특성을 제거하고 다른 특성만 사용",
            "장점": "데이터 일관성 확보",
            "단점": "예측력 저하 가능",
            "구현": "Feature Engineering에서 oi_growth_7d 제거"
        }
    ]
    
    for sol in solutions:
        print(f"\n{sol['방안']}")
        print(f"   설명: {sol['설명']}")
        print(f"   장점: {sol['장점']}")
        print(f"   단점: {sol['단점']}")
        print(f"   구현: {sol['구현']}")

def main():
    print("=" * 80)
    print("🔍 Open Interest 데이터 수집 대체 방법 연구")
    print("=" * 80)
    
    # Coinglass API 테스트
    coinglass_available = test_coinglass_api()
    
    # 대체 소스 연구
    alternatives = research_alternative_sources()
    
    # 해결 방안 제시
    suggest_solutions()
    
    print("\n" + "=" * 80)
    print("✅ 연구 완료!")
    print("=" * 80)
    
    print("\n📋 권장 사항:")
    print("   1. 매일 자동 수집 스크립트 설정 (장기적 해결책)")
    print("   2. 현재는 OI 특성을 제거하거나 대체 지표 사용")
    print("   3. 유료 API 예산이 있다면 CryptoQuant/Glassnode 고려")

if __name__ == "__main__":
    main()




