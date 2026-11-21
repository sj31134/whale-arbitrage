"""
Comprehensive unit tests for the Investor Subagent suite using Python's standard unittest.
"""
import sys
import unittest
import math
from pathlib import Path

# Add branch/investor_agent to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.core.asset import AssetClass, AssetTier, UniversalSkillScores, ScenarioProfile, ScenarioOutcome, Asset
from src.core.valuation import ValuationEngine
from src.core.scoring_engine import ScoringEngine
from src.strategy.scenario_modeler import ScenarioModeler
from src.strategy.barbell_optimizer import BarbellOptimizer
from src.agent.investor_agent_runner import InvestorAgentRunner


class TestInvestorAgent(unittest.TestCase):

    def test_land_building_decomposition(self):
        engine = ValuationEngine()
        # Initial: 80% Land (800k), 20% Building (200k)
        result = engine.calculate_land_building_decomposition(
            initial_land_value=800000.0,
            initial_building_value=200000.0,
            land_annual_growth_rate=0.05,
            building_depreciation_rate=0.025,
            years=20
        )
        self.assertGreater(result["future_land_value"], 800000.0)
        self.assertLess(result["future_building_value"], 200000.0)
        self.assertGreater(result["land_dominance_ratio"], 0.90)

    def test_margin_of_safety(self):
        engine = ValuationEngine()
        mos = engine.calculate_margin_of_safety(current_price=70.0, intrinsic_value=100.0)
        self.assertAlmostEqual(mos, 0.30, places=3)

    def test_universal_skills_score(self):
        scores = UniversalSkillScores(
            decomposition_score=10.0,
            inelasticity_score=10.0,
            buyer_quality_score=8.0,
            walled_garden_score=8.0,
            spillover_score=8.0
        )
        # 10*0.25 + 10*0.25 + 8*0.20 + 8*0.15 + 8*0.15 = 2.5 + 2.5 + 1.6 + 1.2 + 1.2 = 9.0
        self.assertAlmostEqual(scores.weighted_composite_score, 9.0, places=2)

    def test_scenario_modeler_and_payoff(self):
        scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome("Bull", 0.30, 160.0, 0.60, "Expansion"),
            base_case=ScenarioOutcome("Base", 0.50, 125.0, 0.25, "Base"),
            bear_case=ScenarioOutcome("Bear", 0.20, 90.0, -0.10, "Bear")
        )
        # E[R] = 0.30*0.60 + 0.50*0.25 + 0.20*(-0.10) = 0.285
        self.assertAlmostEqual(scenarios.expected_return, 0.285, places=3)
        self.assertAlmostEqual(scenarios.payoff_ratio, 6.0, places=2)

        modeler = ScenarioModeler(hurdle_rate=0.12, min_payoff_ratio=3.0)
        scores = UniversalSkillScores(9.0, 9.0, 9.0, 9.0, 9.0)
        dummy_asset = Asset(
            id="TEST-1",
            name="Test Prime Asset",
            asset_class=AssetClass.REAL_ESTATE,
            current_price=100.0,
            intrinsic_value_base=125.0,
            tier=AssetTier.CORE,
            skill_scores=scores,
            scenarios=scenarios,
            moat_description="Test Moat",
            bottleneck_role="Test Role",
            margin_of_safety_pct=0.20
        )
        res = modeler.evaluate_asset_scenarios(dummy_asset)
        self.assertTrue(res["hurdle_passed"])
        self.assertTrue(res["payoff_passed"])
        self.assertTrue(res["is_asymmetric_opportunity"])

    def test_investor_agent_full_pipeline(self):
        runner = InvestorAgentRunner()
        results = runner.run_full_investment_pipeline()

        self.assertGreaterEqual(results["total_screened_assets"], 5)
        self.assertGreaterEqual(results["qualified_assets_count"], 3)
        alloc = results["portfolio_allocation"]
        self.assertGreaterEqual(alloc["core_weight_total"], 0.55)
        self.assertLessEqual(alloc["core_weight_total"], 0.70)
        self.assertGreaterEqual(alloc["satellite_weight_total"], 0.25)
        self.assertLessEqual(alloc["satellite_weight_total"], 0.40)
        self.assertIn("portfolio_memo", results)
        self.assertGreaterEqual(len(results["asset_memos"]), 3)


if __name__ == "__main__":
    unittest.main()
