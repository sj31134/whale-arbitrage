"""
Scenario Modeler: Implements 3-stage probabilistic scenario modeling and payoff validation.
"""
from typing import Dict, Any, List
from ..core.asset import Asset, ScenarioProfile


class ScenarioModeler:
    def __init__(self, hurdle_rate: float = 0.12, min_payoff_ratio: float = 3.0):
        self.hurdle_rate = hurdle_rate
        self.min_payoff_ratio = min_payoff_ratio

    def evaluate_asset_scenarios(self, asset: Asset) -> Dict[str, Any]:
        """
        Calculates:
        1. Expected Return E[R] = 0.30*Bull + 0.50*Base + 0.20*Bear
        2. Payoff Ratio = Bull Upside / |Bear Downside|
        3. Hurdle Rate Pass/Fail
        """
        exp_return = asset.scenarios.expected_return
        payoff_ratio = asset.scenarios.payoff_ratio
        hurdle_passed = exp_return >= self.hurdle_rate
        payoff_passed = payoff_ratio >= self.min_payoff_ratio

        return {
            "asset_id": asset.id,
            "asset_name": asset.name,
            "expected_return_pct": exp_return,
            "payoff_ratio": payoff_ratio,
            "hurdle_rate": self.hurdle_rate,
            "hurdle_passed": hurdle_passed,
            "payoff_passed": payoff_passed,
            "is_asymmetric_opportunity": hurdle_passed and payoff_passed
        }

    def rank_assets_by_convexity(self, assets: List[Asset]) -> List[Asset]:
        """
        Ranks assets in descending order of their Expected Value x Payoff Ratio.
        """
        return sorted(
            assets,
            key=lambda a: a.scenarios.expected_return * a.scenarios.payoff_ratio,
            reverse=True
        )
