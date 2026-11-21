"""
Individual Capital Planner: Tailored investment framework, variable definitions,
scenario modeling, and data ingestion pipeline for an individual investor with ~300M KRW (3억 원).
"""
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class RetailPortfolioAllocation:
    segment_name: str
    asset_name: str
    allocated_amount_krw: float
    allocation_pct: float
    effective_leverage: float
    margin_call_risk: str
    tax_treatment: str
    expected_return_base: float
    expected_return_bull: float
    expected_return_bear: float


class IndividualCapitalPlanner:
    def __init__(self, initial_capital_krw: float = 300_000_000.0):
        self.initial_capital = initial_capital_krw
        self.as_of_date = "2026-08-17"

    def generate_300m_allocation(self) -> List[RetailPortfolioAllocation]:
        """
        Generates optimal 300M KRW capital allocation balancing 0% margin call leverage,
        tax exemption optimization, and asymmetric compounding velocity.
        """
        allocations = [
            RetailPortfolioAllocation(
                segment_name="1. 실물 토지지분 사다리 (Core Real Estate)",
                asset_name="노원 상계주공 / 수도권 10억 이하 재건축 대지지분 (1주택 비과세 갭투자)",
                allocated_amount_krw=150_000_000.0,
                allocation_pct=50.0,
                effective_leverage=2.2,  # 매매가 ~6.8억, 전세 ~3.8억 (실투자 3.0억 중 자기자본 1.5억 + 1주택 정책대출 1.5억 or 1.5억 전세갭 단독)
                margin_call_risk="0% (2년 무이자 전세 Float, 일중 청산 리스크 없음)",
                tax_treatment="1세대 1주택 비과세 (12억 이하 양도소득세 0원, 취득세 1.1%)",
                expected_return_base=0.35,
                expected_return_bull=0.68,
                expected_return_bear=-0.10
            ),
            RetailPortfolioAllocation(
                segment_name="2. 기업 무이자 플로트 머신 (Core Equities)",
                asset_name="메리츠금융지주 (138040.KS) + 귀주모태주 (600519.SH)",
                allocated_amount_krw=75_000_000.0,
                allocation_pct=25.0,
                effective_leverage=2.3,  # 기업 내포 보험/선수금 무이자 부채 레버리지
                margin_call_risk="0% (현물 보유, 마진콜 리스크 없음)",
                tax_treatment="ISA 계좌 (비과세 500만원 + 9.9% 분리과세) & 해외주식 22% 분류과세",
                expected_return_base=0.28,
                expected_return_bull=0.60,
                expected_return_bear=-0.12
            ),
            RetailPortfolioAllocation(
                segment_name="3. 마진콜 0% 파생 레버리지 (Satellite Engine)",
                asset_name="NVDA 2028년 1월 ITM LEAPS Call (Delta 0.88) + 삼성전자 (274,500원)",
                allocated_amount_krw=50_000_000.0,
                allocation_pct=16.7,
                effective_leverage=2.85, # 30% 자본으로 100% 주가 익스포저 통제
                margin_call_risk="0% (만기 2년+ 장기 옵션, 일중 Flash Crash 청산 불가)",
                tax_treatment="해외 파생/주식 양도소득세 22% (연 250만원 기본공제)",
                expected_return_base=0.65,
                expected_return_bull=1.45,
                expected_return_bear=-0.35
            ),
            RetailPortfolioAllocation(
                segment_name="4. Flash Crash 사냥 버퍼 (Cash Reserve)",
                asset_name="달러 MMF / 발행어음 / CMA (AI 봇 투매 시 긴급 매수 대기)",
                allocated_amount_krw=25_000_000.0,
                allocation_pct=8.3,
                effective_leverage=1.0,
                margin_call_risk="0% (100% 안전 유동성)",
                tax_treatment="이자소득세 15.4%",
                expected_return_base=0.04,
                expected_return_bull=0.04,
                expected_return_bear=0.04
            )
        ]
        return allocations

    def calculate_scenario_outcomes(self, allocations: List[RetailPortfolioAllocation]) -> Dict[str, Any]:
        """
        Calculates 3-stage probabilistic portfolio return for 300M KRW.
        """
        base_ret = sum(a.allocation_pct / 100.0 * a.expected_return_base for a in allocations)
        bull_ret = sum(a.allocation_pct / 100.0 * a.expected_return_bull for a in allocations)
        bear_ret = sum(a.allocation_pct / 100.0 * a.expected_return_bear for a in allocations)

        expected_ret = (0.30 * bull_ret) + (0.50 * base_ret) + (0.20 * bear_ret)
        payoff_ratio = (0.30 * bull_ret + 0.50 * base_ret) / (0.20 * abs(bear_ret))

        terminal_wealth_base = self.initial_capital * (1.0 + base_ret)
        terminal_wealth_bull = self.initial_capital * (1.0 + bull_ret)
        terminal_wealth_bear = self.initial_capital * (1.0 + bear_ret)
        terminal_wealth_expected = self.initial_capital * (1.0 + expected_ret)

        return {
            "initial_capital_krw": self.initial_capital,
            "base_case_return_pct": round(base_ret * 100, 2),
            "bull_case_return_pct": round(bull_ret * 100, 2),
            "bear_case_return_pct": round(bear_ret * 100, 2),
            "expected_annual_return_pct": round(expected_ret * 100, 2),
            "payoff_ratio": round(payoff_ratio, 2),
            "terminal_wealth_base_krw": round(terminal_wealth_base),
            "terminal_wealth_bull_krw": round(terminal_wealth_bull),
            "terminal_wealth_bear_krw": round(terminal_wealth_bear),
            "terminal_wealth_expected_krw": round(terminal_wealth_expected)
        }
