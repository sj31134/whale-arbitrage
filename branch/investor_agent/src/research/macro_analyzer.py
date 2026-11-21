"""
Macro Analyzer: Tracks macro tailwinds, interest rates, liquidity cycles, and structural paradigm shifts.
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class MacroRegime:
    fed_funds_rate: float            # e.g., 0.045 (4.5%)
    us_10y_yield: float              # e.g., 0.041 (4.1%)
    global_m2_growth_yoy: float      # e.g., 0.065 (+6.5%)
    inflation_cpi_yoy: float         # e.g., 0.028 (+2.8%)
    energy_grid_capex_cycle: str     # "High Expansion"
    ai_datacenter_power_demand: str  # "Acute Shortage"
    geopolitical_fragmentation: str  # "High (Deglobalization)"

    @property
    def is_hard_asset_favorable(self) -> bool:
        # Favorable when real rates are moderate/falling and global M2 expansion + geopolitical risks are high
        return self.global_m2_growth_yoy > 0.04 or self.geopolitical_fragmentation in ["High (Deglobalization)", "Severe"]

    @property
    def is_power_bottleneck_critical(self) -> bool:
        return self.ai_datacenter_power_demand in ["Acute Shortage", "Expanding"]


class MacroAnalyzer:
    def __init__(self, current_regime: MacroRegime = None):
        if current_regime is None:
            self.regime = MacroRegime(
                fed_funds_rate=0.0425,
                us_10y_yield=0.040,
                global_m2_growth_yoy=0.072,
                inflation_cpi_yoy=0.029,
                energy_grid_capex_cycle="High Expansion",
                ai_datacenter_power_demand="Acute Shortage",
                geopolitical_fragmentation="High (Deglobalization)"
            )
        else:
            self.regime = current_regime

    def get_macro_summary(self) -> Dict[str, str]:
        return {
            "Liquidity Regime": "M2 Expansion (+7.2% YoY)",
            "Interest Rate Environment": f"10Y Yield at {self.regime.us_10y_yield * 100:.1f}%",
            "Top Structural Tailwinds": "1. AI Silicon & Advanced Packaging | 2. Grid Transformers & Energy Infrastructure | 3. Hard Monetary Anchors (Gold)",
            "Anti-fragility Stance": "Favor physical supply constraints over commoditized software layers."
        }
