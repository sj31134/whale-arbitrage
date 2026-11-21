"""
Unit Tests for RealEstateSubagent (Tier 2-B Dedicated Domain Specialist):
Tests 3-Gate Veto, 7-Step Court Auction Rights, Land Decomposition, and End-to-End Pipeline Execution.
"""
import sys
import unittest
from pathlib import Path

# Add branch/investor_agent to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.subagents.real_estate.real_estate_subagent import RealEstateSubagent


class TestRealEstateSubagent(unittest.TestCase):

    def setUp(self):
        self.subagent = RealEstateSubagent()

    def test_screen_land_candidate_pass(self):
        res = self.subagent.screen_land_candidate(
            candidate_id="RE-YONGSAN-001",
            name="Yongsan Moa-Town Land Share",
            real_price_eok=8.5,
            real_jeonse_eok=4.5,
            land_area_pyeong=8.4,
            intrinsic_value_eok=12.0,
            is_oversupplied_periphery=False,
            has_high_income_cohort=True,
            location_compounding_factor=1.25
        )
        self.assertTrue(res["is_qualified"])
        self.assertGreater(res["margin_of_safety"], 0.3)
        self.assertIn("게이트 통과", res["veto_reason"])

    def test_screen_land_candidate_veto_oversupplied_periphery(self):
        res = self.subagent.screen_land_candidate(
            candidate_id="RE-YANGJU-001",
            name="Yangju Greenfield High-Density Apt",
            real_price_eok=3.8,
            real_jeonse_eok=3.5,
            land_area_pyeong=14.0,
            intrinsic_value_eok=4.0,
            is_oversupplied_periphery=True,
            has_high_income_cohort=False
        )
        self.assertFalse(res["is_qualified"])
        self.assertIn("100% VETO", res["veto_reason"])

    def test_court_auction_safe_with_hug_waiver(self):
        report = self.subagent.analyze_court_auction(
            case_number="2025타경10424-TEST",
            court_name="서울서부지법",
            auction_date="2026-09-08",
            bidding_round="3회차 (64%)",
            location="용산구 원효로1가 빌라",
            property_type="재개발 빌라 대지지분",
            appraisal_value=850_000_000,
            min_bid_price=544_000_000,
            land_area_pyeong=8.4,
            registry_rights=[
                {"type": "근저당", "date": "2021-03-15", "amount": 300_000_000}
            ],
            tenant_data=[
                {
                    "name": "선순위임차인",
                    "move_in_date": "2020-05-10",
                    "deposit": 280_000_000,
                    "demanded_dividend": True
                }
            ],
            has_hug_waiver=True
        )
        self.assertEqual(report.total_acquisition_liability, 0.0)
        self.assertEqual(report.safety_score, 10.0)
        self.assertIn("초특급 알파", report.final_verdict)

    def test_court_auction_unsafe_undemanded_dividend(self):
        report = self.subagent.analyze_court_auction(
            case_number="2025타경51203-TEST",
            court_name="서울북부지법",
            auction_date="2026-09-29",
            bidding_round="3회차 (64%)",
            location="노원구 상계동 주공",
            property_type="재건축 아파트 대지지분",
            appraisal_value=680_000_000,
            min_bid_price=435_200_000,
            land_area_pyeong=12.1,
            registry_rights=[
                {"type": "근저당", "date": "2022-04-10", "amount": 250_000_000}
            ],
            tenant_data=[
                {
                    "name": "미배당임차인",
                    "move_in_date": "2021-01-15",
                    "deposit": 220_000_000,
                    "demanded_dividend": False
                }
            ],
            has_hug_waiver=False
        )
        self.assertEqual(report.total_acquisition_liability, 220_000_000)
        self.assertLess(report.safety_score, 8.0)
        self.assertIn("주의 물건", report.final_verdict)

    def test_september_october_auction_cases_count_and_filter(self):
        all_cases = self.subagent.get_september_october_auction_cases()
        self.assertGreaterEqual(len(all_cases), 8)

        sep_reports = self.subagent.analyze_scheduled_court_auctions(month_filter="2026-09")
        self.assertGreaterEqual(len(sep_reports), 5)
        for r in sep_reports:
            self.assertTrue(r.auction_date.startswith("2026-09"))

    def test_run_subagent_pipeline(self):
        results = self.subagent.run_subagent_pipeline(auction_month_filter="all")
        self.assertGreaterEqual(results["total_candidates_screened"], 12)
        self.assertGreaterEqual(results["passed_candidates_count"], 8)
        self.assertGreaterEqual(results["vetoed_traps_count"], 2)
        self.assertGreaterEqual(results["auction_reports_count"], 8)
        self.assertIn("subagent_memo", results)
        self.assertIn("2026년 9월·10월", results["subagent_memo"])


if __name__ == "__main__":
    unittest.main()
