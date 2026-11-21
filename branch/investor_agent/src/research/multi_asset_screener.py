"""
Multi-Asset Screener: Analyzes across Real Estate, Equities, Commodities, and Crypto/RWA.
"""
from typing import List, Dict
from ..core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from ..core.valuation import ValuationEngine
from ..core.scoring_engine import ScoringEngine


class MultiAssetScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()

    def get_curated_universe(self) -> List[Asset]:
        """
        Returns deeply researched assets across all 4 asset classes evaluated with the 5 Universal Skills.
        """
        assets: List[Asset] = []

        # 1. Real Estate: Hannam UN Village Prime Land Plot
        re_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.5,   # >85% land value, building depreciates to 0 without loss
            inelasticity_score=10.0,  # South-facing Han Riverfront + Namsan mountain: physically uncloneable
            buyer_quality_score=9.8,  # UHNWI, 100% cash, zero debt/LTV sensitivity
            walled_garden_score=9.2,  # Peninsula dead-end topography, extreme privacy moat
            spillover_score=9.0       # Hannam New Town redevelopment infrastructure spillover
        )
        re_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=160.0, expected_return_pct=0.60, catalyst_description="Hannam New Town completion & super-luxury spillover consolidation"),
            base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=125.0, expected_return_pct=0.25, catalyst_description="Steady prime land inflation compounding"),
            bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=95.0, expected_return_pct=-0.05, catalyst_description="Macro real estate freeze; cash buyer hard floor holds value")
        )
        assets.append(Asset(
            id="RE-HANNAM-UN",
            name="Hannam UN Village Prime Land Plot",
            asset_class=AssetClass.REAL_ESTATE,
            current_price=100.0,
            intrinsic_value_base=135.0,
            tier=AssetTier.CORE,
            skill_scores=re_scores,
            scenarios=re_scenarios,
            moat_description="Permanent natural monopoly: South-facing Han River view, peninsula privacy fortress, ultra-high land share.",
            bottleneck_role="Physical spatial monopoly for Top 0.01% UHNWI.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(100.0, 135.0),
            thesis_invalidation_triggers=[
                "Structural zoning law changes permitting high-rise mass development on UN Village peninsula",
                "Severe geographic/environmental degradation of central Seoul Han riverfront"
            ]
        ))

        # 2. Equities: TSMC (Taiwan Semiconductor Manufacturing Co.)
        tsm_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=8.5,   # Deep moat in advanced packaging (CoWoS) and foundry ecosystem
            inelasticity_score=9.5,   # >90% market share in sub-3nm nodes; zero substitute in short/mid term
            buyer_quality_score=9.0,   # Nvidia, Apple, AMD, Qualcomm (Trillion-dollar balance sheets)
            walled_garden_score=8.5,   # Closed OIP (Open Innovation Platform) design IP ecosystem
            spillover_score=9.5        # Captures hundreds of billions in Big Tech AI infrastructure Capex
        )
        tsm_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=260.0, expected_return_pct=0.73, catalyst_description="Accelerated AI ASIC and GPU packaging volume doubling"),
            base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=190.0, expected_return_pct=0.26, catalyst_description="Sustained pricing power (+10% ASP hikes) & high ROIC"),
            bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=130.0, expected_return_pct=-0.13, catalyst_description="Geopolitical escalation / Taiwan Strait disruption")
        )
        assets.append(Asset(
            id="EQ-TSMC",
            name="TSMC (Taiwan Semiconductor Manufacturing Co.)",
            asset_class=AssetClass.EQUITIES,
            current_price=150.0,
            intrinsic_value_base=195.0,
            tier=AssetTier.SATELLITE,
            skill_scores=tsm_scores,
            scenarios=tsm_scenarios,
            moat_description="Irreplaceable manufacturing bottleneck for advanced silicon; massive Capex/R&D barrier (> $30B/yr).",
            bottleneck_role="Single Point of Failure (SPOF) for global AI & High-Performance Computing.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(150.0, 195.0),
            thesis_invalidation_triggers=[
                "Intel 18A/14A or Samsung achieving superior yields at lower cost on leading-edge nodes",
                "Direct kinetic conflict across Taiwan Strait (Black Swan)"
            ]
        ))

        # 3. Equities / Infrastructure: Eaton Corp (Power Grid & Transformer Bottleneck)
        etn_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=8.0,   # Sticky utility contracts & high recurring component upgrades
            inelasticity_score=9.0,   # Multi-year backlog for high-voltage transformers (3-4 year lead times)
            buyer_quality_score=9.2,   # Hyperscalers (Microsoft, AWS) and regulated electric utilities
            walled_garden_score=8.0,   # Utility qualification specs and mission-critical reliability certifications
            spillover_score=9.0        # Free-riding on global grid modernization and data center power demand
        )
        etn_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=420.0, expected_return_pct=0.50, catalyst_description="Hyper-acceleration in multi-gigawatt data center grid tie-ins"),
            base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=340.0, expected_return_pct=0.21, catalyst_description="Order backlog execution with widening operating margins"),
            bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=250.0, expected_return_pct=-0.10, catalyst_description="Utility Capex pause due to debt financing constraints")
        )
        assets.append(Asset(
            id="EQ-EATON",
            name="Eaton Corporation (Power Grid Infrastructure)",
            asset_class=AssetClass.EQUITIES,
            current_price=280.0,
            intrinsic_value_base=345.0,
            tier=AssetTier.SATELLITE,
            skill_scores=etn_scores,
            scenarios=etn_scenarios,
            moat_description="Physical bottleneck in power distribution, circuit protection, and custom high-voltage switchgear.",
            bottleneck_role="Critical physical gatekeeper for AI data center electrification.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(280.0, 345.0),
            thesis_invalidation_triggers=[
                "Massive unexpected flood of low-cost, qualified transformer manufacturing from emerging markets",
                "Sharp decline in global electricity grid capital investment"
            ]
        ))

        # 4. Commodities: Physical Allocated Gold
        gold_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=10.0,  # Pure 100% hard asset, zero building/wrapper depreciation
            inelasticity_score=9.0,   # Geological scarcity with ~1.5% annual stock-to-flow production
            buyer_quality_score=9.5,   # Global central banks (PBoC, RBI) and sovereign wealth funds
            walled_garden_score=7.0,   # Outside counterparty risk of sovereign fiat banking system
            spillover_score=8.5        # Gains purchasing power from unlimited global fiat debt expansion
        )
        gold_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=3300.0, expected_return_pct=0.37, catalyst_description="Accelerated central bank de-dollarization and reserve diversification"),
            base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=2750.0, expected_return_pct=0.14, catalyst_description="Continuous M2 inflation tracking & real yield moderation"),
            bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=2200.0, expected_return_pct=-0.08, catalyst_description="Extended regime of ultra-high real interest rates")
        )
        assets.append(Asset(
            id="CMD-GOLD",
            name="Physical Allocated Gold (Bullion Vault / XAU)",
            asset_class=AssetClass.COMMODITIES,
            current_price=2400.0,
            intrinsic_value_base=2800.0,
            tier=AssetTier.CORE,
            skill_scores=gold_scores,
            scenarios=gold_scenarios,
            moat_description="5,000-year track record as un-debasable neutral monetary reserve asset without counterparty risk.",
            bottleneck_role="Ultimate collateral anchor of last resort in deglobalization.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(2400.0, 2800.0),
            thesis_invalidation_triggers=[
                "Permanent global fiscal austerity and credible return to hard-pegged sovereign fiat discipline",
                "Discovery of commercial-scale asteroid mining delivering cheap gold supply"
            ]
        ))

        # 5. Crypto: Bitcoin (Digital Reserve & Hard Cap Blockspace)
        btc_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.0,   # Hard-coded 21M mathematical cap, pure monetary protocol
            inelasticity_score=10.0,  # Difficulty adjustment enforces absolute programmatic inelasticity
            buyer_quality_score=8.5,   # Institutional ETF holders, corporate treasuries, sovereign adopters
            walled_garden_score=8.8,   # Highest SHA-256 Proof-of-Work hashrate defense
            spillover_score=9.0        # Free-rides on internet bandwidth, energy grid monetization, ETF access
        )
        btc_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=160000.0, expected_return_pct=1.46, catalyst_description="Nation-state adoption & sovereign wealth fund allocation"),
            base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=95000.0, expected_return_pct=0.46, catalyst_description="Institutional allocation expansion (1-3% model portfolios)"),
            bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=45000.0, expected_return_pct=-0.30, catalyst_description="Coordinated G7 regulatory clampdown or macro liquidity drain")
        )
        assets.append(Asset(
            id="CRYPTO-BTC",
            name="Bitcoin (Digital Hard Reserve)",
            asset_class=AssetClass.CRYPTO_RWA,
            current_price=65000.0,
            intrinsic_value_base=95000.0,
            tier=AssetTier.SATELLITE,
            skill_scores=btc_scores,
            scenarios=btc_scenarios,
            moat_description="First-mover monetary network effect with unbreakable cryptographic supply limit.",
            bottleneck_role="Decentralized censorship-resistant settlement layer.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(65000.0, 95000.0),
            thesis_invalidation_triggers=[
                "Catastrophic cryptographic vulnerability in SHA-256 or ECDSA secp256k1",
                "Consensus failure leading to contentious unfixable chain split"
            ]
        ))

        return assets
