"""
Barbell Portfolio Optimizer: Allocates capital between Core (60-70%) and Satellite (30-40%),
explicitly factoring in Margin of Safety (Entry Price Cheapness) and Moat Convexity.
"""
from typing import List, Dict, Any
from ..core.asset import Asset, AssetTier


class BarbellOptimizer:
    def __init__(
        self,
        core_target_weight: float = 0.65,      # 65% Core
        satellite_target_weight: float = 0.35,  # 35% Satellite
        cash_buffer: float = 0.05               # 5% Cash reserve
    ):
        self.core_target_weight = core_target_weight
        self.satellite_target_weight = satellite_target_weight
        self.cash_buffer = cash_buffer

    def optimize_allocation(self, qualified_assets: List[Asset]) -> Dict[str, Any]:
        """
        Distributes capital across Core and Satellite buckets based on skill scores,
        convexity, and explicit Margin of Safety (cheapness) scaling.
        """
        core_assets = [a for a in qualified_assets if a.tier == AssetTier.CORE]
        satellite_assets = [a for a in qualified_assets if a.tier == AssetTier.SATELLITE]

        allocated_portfolio: List[Dict[str, Any]] = []

        # Effective investable pool (excluding cash buffer)
        investable_capital = 1.0 - self.cash_buffer
        effective_core_budget = investable_capital * self.core_target_weight
        effective_satellite_budget = investable_capital * self.satellite_target_weight

        # 1. Allocate Core (Weighted by Moat Score * Margin of Safety Multiplier)
        if core_assets:
            total_core_score = sum(
                a.skill_scores.weighted_composite_score * (1.0 + max(0.0, a.margin_of_safety_pct))
                for a in core_assets
            )
            for a in core_assets:
                score_factor = a.skill_scores.weighted_composite_score * (1.0 + max(0.0, a.margin_of_safety_pct))
                weight = effective_core_budget * (score_factor / total_core_score)
                a.recommended_weight_pct = weight
                allocated_portfolio.append({
                    "asset_id": a.id,
                    "asset_name": a.name,
                    "tier": a.tier.value,
                    "asset_class": a.asset_class.value,
                    "recommended_weight_pct": weight,
                    "expected_return_pct": a.scenarios.expected_return,
                    "payoff_ratio": a.scenarios.payoff_ratio,
                    "margin_of_safety_pct": a.margin_of_safety_pct,
                    "composite_score": a.skill_scores.weighted_composite_score
                })

        # 2. Allocate Satellite (Weighted by Convexity * Margin of Safety Multiplier)
        if satellite_assets:
            total_sat_score = sum(
                (a.scenarios.expected_return * a.scenarios.payoff_ratio) * (1.0 + max(0.0, a.margin_of_safety_pct))
                for a in satellite_assets
            )
            for a in satellite_assets:
                sat_factor = (a.scenarios.expected_return * a.scenarios.payoff_ratio) * (1.0 + max(0.0, a.margin_of_safety_pct))
                weight = effective_satellite_budget * (sat_factor / total_sat_score)
                a.recommended_weight_pct = weight
                allocated_portfolio.append({
                    "asset_id": a.id,
                    "asset_name": a.name,
                    "tier": a.tier.value,
                    "asset_class": a.asset_class.value,
                    "recommended_weight_pct": weight,
                    "expected_return_pct": a.scenarios.expected_return,
                    "payoff_ratio": a.scenarios.payoff_ratio,
                    "margin_of_safety_pct": a.margin_of_safety_pct,
                    "composite_score": a.skill_scores.weighted_composite_score
                })

        # 3. Synchronized Bear Case Stress Test
        portfolio_bear_return = sum(
            a.recommended_weight_pct * a.scenarios.bear_case.expected_return_pct
            for a in (core_assets + satellite_assets)
        )
        # Add cash buffer contribution in bear market (0% drawdown on cash)
        # portfolio_bear_return remains protected

        # Expected overall return
        portfolio_expected_return = sum(
            a.recommended_weight_pct * a.scenarios.expected_return
            for a in (core_assets + satellite_assets)
        )

        core_weight_sum = sum(a.recommended_weight_pct for a in core_assets)
        sat_weight_sum = sum(a.recommended_weight_pct for a in satellite_assets)

        return {
            "allocated_assets": allocated_portfolio,
            "portfolio": allocated_portfolio,
            "core_budget_pct": effective_core_budget,
            "satellite_budget_pct": effective_satellite_budget,
            "core_weight_total": core_weight_sum,
            "satellite_weight_total": sat_weight_sum,
            "cash_buffer_weight": self.cash_buffer,
            "cash_buffer_pct": self.cash_buffer,
            "portfolio_expected_return_pct": portfolio_expected_return,
            "portfolio_bear_return_pct": portfolio_bear_return,
            "drawdown_limit_met": portfolio_bear_return >= -0.20  # Max acceptable loss is <= 20%
        }

