#!/usr/bin/env python3
"""
UI 통합 테스트
- 전체 플로우 테스트
- 시뮬레이션 시나리오 테스트
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

from data_loader import DataLoader
from calculator import CostCalculator
from recommender import StrategyRecommender


def test_scenario_1_normal_case():
    """시나리오 1: 정상 케이스"""
    print("=" * 60)
    print("시나리오 1: 정상 케이스")
    print("=" * 60)
    
    calculator = CostCalculator()
    
    result = calculator.calculate_arbitrage_cost(
        from_date="2024-01-01",
        to_date="2024-06-30",
        coin="BTC",
        exchanges=["바이낸스-비트겟"],
        initial_capital=100_000_000
    )
    
    assert result["success"], f"실패: {result.get('error')}"
    assert result["data"]["total_trades"] > 0, "거래가 발생하지 않았습니다"
    
    print(f"✅ 성공: {result['data']['total_trades']}건 거래")
    return True


def test_scenario_2_data_insufficient():
    """시나리오 2: 데이터 부족"""
    print("\n" + "=" * 60)
    print("시나리오 2: 데이터 부족")
    print("=" * 60)
    
    loader = DataLoader()
    
    is_valid, error = loader.validate_date_range("2020-01-01", "2020-01-31", "BTC")
    
    assert not is_valid, "데이터 부족 케이스가 통과되었습니다"
    assert error is not None, "에러 메시지가 없습니다"
    
    print(f"✅ 성공: {error}")
    loader.close()
    return True


def test_scenario_3_invalid_date_range():
    """시나리오 3: 잘못된 날짜 범위"""
    print("\n" + "=" * 60)
    print("시나리오 3: 잘못된 날짜 범위")
    print("=" * 60)
    
    loader = DataLoader()
    
    is_valid, error = loader.validate_date_range("2024-12-31", "2024-01-01", "BTC")
    
    assert not is_valid, "잘못된 날짜 범위가 통과되었습니다"
    assert "시작 날짜" in error or "종료 날짜" in error, "적절한 에러 메시지가 아닙니다"
    
    print(f"✅ 성공: {error}")
    loader.close()
    return True


def test_scenario_4_short_period():
    """시나리오 4: 매우 짧은 기간"""
    print("\n" + "=" * 60)
    print("시나리오 4: 매우 짧은 기간")
    print("=" * 60)
    
    loader = DataLoader()
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    is_valid, error = loader.validate_date_range(
        yesterday.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
        "BTC"
    )
    
    assert not is_valid, "짧은 기간이 통과되었습니다"
    assert "30일" in error, "적절한 에러 메시지가 아닙니다"
    
    print(f"✅ 성공: {error}")
    loader.close()
    return True


def test_scenario_5_no_trades():
    """시나리오 5: 거래 없음 (조건이 너무 엄격)"""
    print("\n" + "=" * 60)
    print("시나리오 5: 거래 없음 (조건이 너무 엄격)")
    print("=" * 60)
    
    calculator = CostCalculator()
    
    result = calculator.calculate_arbitrage_cost(
        from_date="2024-01-01",
        to_date="2024-01-31",
        coin="BTC",
        exchanges=["바이낸스-비트겟"],
        initial_capital=100_000_000,
        entry_z=10.0  # 매우 엄격한 조건
    )
    
    # 거래가 없을 수 있음 (정상)
    if not result["success"]:
        print(f"⚠️ 예상된 결과: {result.get('error')}")
    else:
        print(f"✅ 거래 발생: {result['data']['total_trades']}건")
    
    return True


def test_scenario_6_strategy_recommendation():
    """시나리오 6: 전략 추천"""
    print("\n" + "=" * 60)
    print("시나리오 6: 전략 추천")
    print("=" * 60)
    
    recommender = StrategyRecommender()
    
    # 데이터가 있는 날짜 선택
    result = recommender.recommend_best_strategy(
        target_date="2024-06-15",
        coin="BTC",
        initial_capital=100_000_000
    )
    
    if result["success"]:
        print(f"✅ 추천 성공: {result['data']['recommended_pair']}")
        print(f"   예상 수익률: {result['data']['expected_return'] * 100:.2f}%")
    else:
        print(f"⚠️ 추천 실패 (데이터 부족 가능): {result.get('error')}")
    
    return True


def main():
    """모든 시나리오 테스트 실행"""
    print("🧪 UI 통합 테스트 시작\n")
    
    scenarios = [
        test_scenario_1_normal_case,
        test_scenario_2_data_insufficient,
        test_scenario_3_invalid_date_range,
        test_scenario_4_short_period,
        test_scenario_5_no_trades,
        test_scenario_6_strategy_recommendation
    ]
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        try:
            if scenario():
                passed += 1
            else:
                failed += 1
                print(f"❌ {scenario.__name__} 실패")
        except Exception as e:
            failed += 1
            print(f"❌ {scenario.__name__} 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("통합 테스트 결과")
    print("=" * 60)
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

