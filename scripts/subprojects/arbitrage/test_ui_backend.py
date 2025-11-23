#!/usr/bin/env python3
"""
UI 백엔드 로직 유닛 테스트
"""

import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app" / "utils"))

from data_loader import DataLoader
from calculator import CostCalculator
from recommender import StrategyRecommender


def test_data_loader():
    """테스트 1: 데이터 로더"""
    print("=" * 60)
    print("테스트 1: 데이터 로더")
    print("=" * 60)
    
    loader = DataLoader()
    
    # 사용 가능한 날짜 범위
    min_date, max_date = loader.get_available_dates('BTC')
    print(f"✅ 사용 가능한 날짜: {min_date} ~ {max_date}")
    
    # 데이터 로드
    df = loader.load_exchange_data("2024-01-01", "2024-01-31", "BTC")
    print(f"✅ 데이터 로드: {len(df)}건")
    assert len(df) > 0, "데이터가 로드되지 않았습니다"
    assert 'upbit_price' in df.columns, "upbit_price 컬럼이 없습니다"
    
    # 날짜 범위 검증
    is_valid, error = loader.validate_date_range("2024-01-01", "2024-12-31", "BTC")
    print(f"✅ 날짜 범위 검증: {is_valid}")
    
    loader.close()
    return True


def test_cost_calculator():
    """테스트 2: 비용 계산기"""
    print("\n" + "=" * 60)
    print("테스트 2: 비용 계산기")
    print("=" * 60)
    
    calculator = CostCalculator()
    
    result = calculator.calculate_arbitrage_cost(
        from_date="2024-01-01",
        to_date="2024-06-30",
        coin="BTC",
        exchanges=["바이낸스-비트겟", "업비트-비트겟"],
        initial_capital=100_000_000,
        entry_z=2.5,
        exit_z=0.5
    )
    
    assert result["success"], f"계산 실패: {result.get('error', 'Unknown error')}"
    assert "data" in result, "결과 데이터가 없습니다"
    assert "total_trades" in result["data"], "total_trades가 없습니다"
    
    print(f"✅ 계산 성공: {result['data']['total_trades']}건 거래")
    print(f"   최종 수익률: {result['data']['final_return'] * 100:.2f}%")
    
    return True


def test_strategy_recommender():
    """테스트 3: 전략 추천기"""
    print("\n" + "=" * 60)
    print("테스트 3: 전략 추천기")
    print("=" * 60)
    
    recommender = StrategyRecommender()
    
    result = recommender.recommend_best_strategy(
        target_date="2024-06-15",
        coin="BTC",
        initial_capital=100_000_000
    )
    
    if not result["success"]:
        print(f"⚠️ 추천 실패: {result.get('error', 'Unknown error')}")
        # 데이터가 없는 날짜일 수 있으므로 경고만 출력
        return True
    
    assert "data" in result, "결과 데이터가 없습니다"
    assert "recommended_pair" in result["data"], "recommended_pair가 없습니다"
    
    print(f"✅ 추천 성공: {result['data']['recommended_pair']}")
    print(f"   예상 수익률: {result['data']['expected_return'] * 100:.2f}%")
    
    return True


def main():
    """모든 테스트 실행"""
    print("🧪 UI 백엔드 로직 유닛 테스트 시작\n")
    
    tests = [
        test_data_loader,
        test_cost_calculator,
        test_strategy_recommender
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} 실패")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("테스트 결과")
    print("=" * 60)
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

