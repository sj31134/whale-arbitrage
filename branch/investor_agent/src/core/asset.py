"""
Core domain models and abstractions for the Investor Subagent.
"""
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum


class AssetTier(str, Enum):
    CORE = "Core"              # 60~70% of Portfolio (Geographic Monopolies, Hard Assets, Non-cyclicals)
    SATELLITE = "Satellite"    # 30~40% of Portfolio (Industrial Bottlenecks, Cluster Nodes, Asymmetric Bets)
    UNQUALIFIED = "Unqualified"# Failed Hurdle Rate or Asymmetric Payoff


class AssetClass(str, Enum):
    REAL_ESTATE = "Real Estate"
    EQUITIES = "Equities & Infrastructure"
    COMMODITIES = "Commodities & Hard Assets"
    CRYPTO_RWA = "Crypto & RWA"


@dataclass
class Principles11Scorecard:
    """
    11-Principle Hierarchical Weighting Framework:
    - Level 1: Core Axioms & Economic Moats (35% Weight)
    - Level 2: Capital Velocity, Float Leverage & Asymmetric Payoffs (30% Weight)
    - Level 3: Market Dynamics & Policy Transmission (20% Weight)
    - Level 4: Data Verification & System Integrity (15% Weight)
    """
    # Level 1: Core Axioms & Economic Moats (35%)
    p1_decomposition_score: float = 9.0        # Weight 15%: Asset Value Decomposition V(t) = Land(e^gt) + Bldg(0)
    p2_fundamental_fcf_score: float = 9.0      # Weight 12%: FCF, Pricing Power, ROIC > WACC
    p3_universal_skills_score: float = 9.0     # Weight 8%: Supply Inelasticity & Walled Garden Moats

    # Level 2: Capital Velocity & Asymmetry (30%)
    p4_float_leverage_velocity: float = 9.0    # Weight 10%: Non-Callable Jeonse/Float & Re-rating Harvest
    p9_scenario_asymmetry_score: float = 9.0   # Weight 10%: Payoff >= 3.0x, Hurdle >= 12%, MoS >= 20%
    p10_barbell_downside_protect: float = 9.0  # Weight 10%: Core 65% stability, Max Bear Drawdown <= 20%

    # Level 3: Market Dynamics & Policy Harness (20%)
    p5_time_horizon_arbitrage: float = 9.0     # Weight 7%: Exploiting Quant/Algo/Pod Shop forced selling
    p6_policy_transmission_score: float = 9.0  # Weight 7%: IRA 45U, TSE PBR 1x, Value-Up, Big Fund 3
    p7_universe_ladder_score: float = 9.0      # Weight 6%: Global multi-asset & sub-10억 capital ladder

    # Level 4: Data Verification & System Integrity (15%)
    p8_data_verification_score: float = 9.5    # Weight 10%: Tier-1 SEC/DART/국토교통부 100% fact-checked
    p11_workflow_integrity_score: float = 9.5  # Weight 5%: Dual-layer storage & knowledge graph sound

    @property
    def hierarchical_composite_score(self) -> float:
        return (
            self.p1_decomposition_score * 0.15 +
            self.p2_fundamental_fcf_score * 0.12 +
            self.p3_universal_skills_score * 0.08 +
            self.p4_float_leverage_velocity * 0.10 +
            self.p9_scenario_asymmetry_score * 0.10 +
            self.p10_barbell_downside_protect * 0.10 +
            self.p5_time_horizon_arbitrage * 0.07 +
            self.p6_policy_transmission_score * 0.07 +
            self.p7_universe_ladder_score * 0.06 +
            self.p8_data_verification_score * 0.10 +
            self.p11_workflow_integrity_score * 0.05
        )


@dataclass
class UniversalSkillScores:
    decomposition_score: float      # Skill 1: Shell vs Core (0 - 10)
    inelasticity_score: float       # Skill 2: Supply Inelasticity (0 - 10)
    buyer_quality_score: float      # Skill 3: Price-Inelastic Buyer Cohort (0 - 10)
    walled_garden_score: float      # Skill 4: Walled Garden & Privacy Moat (0 - 10)
    spillover_score: float          # Skill 5: Spillover Arbitrage (0 - 10)

    @property
    def weighted_composite_score(self) -> float:
        # Standard weights: 25%, 25%, 20%, 15%, 15%
        return (
            self.decomposition_score * 0.25 +
            self.inelasticity_score * 0.25 +
            self.buyer_quality_score * 0.20 +
            self.walled_garden_score * 0.15 +
            self.spillover_score * 0.15
        )


@dataclass
class ScenarioOutcome:
    name: str                       # "Bull", "Base", "Bear"
    probability: float              # e.g., 0.30, 0.50, 0.20
    target_price: float             # Expected target price in this scenario
    expected_return_pct: float      # Return percentage (e.g., 0.60 for +60%, -0.15 for -15%)
    catalyst_description: str = ""  # Key operational/macro catalyst for this scenario


@dataclass
class ScenarioProfile:
    bull_case: ScenarioOutcome
    base_case: ScenarioOutcome
    bear_case: ScenarioOutcome

    @property
    def expected_return(self) -> float:
        return (
            self.bull_case.probability * self.bull_case.expected_return_pct +
            self.base_case.probability * self.base_case.expected_return_pct +
            self.bear_case.probability * self.bear_case.expected_return_pct
        )

    @property
    def payoff_ratio(self) -> float:
        # Upside (Bull Return) / Downside (|Bear Return|)
        downside = abs(self.bear_case.expected_return_pct)
        if downside == 0:
            return 999.0
        return self.bull_case.expected_return_pct / downside


@dataclass
class Asset:
    id: str
    name: str
    asset_class: AssetClass
    current_price: float
    intrinsic_value_base: float
    tier: AssetTier
    skill_scores: UniversalSkillScores
    scenarios: ScenarioProfile
    moat_description: str
    bottleneck_role: str
    margin_of_safety_pct: float
    recommended_weight_pct: float = 0.0
    thesis_invalidation_triggers: List[str] = field(default_factory=list)

    @property
    def is_investable(self) -> bool:
        return (
            self.skill_scores.weighted_composite_score >= 7.0 and
            self.scenarios.payoff_ratio >= 3.0 and
            self.margin_of_safety_pct >= 0.15
        )
