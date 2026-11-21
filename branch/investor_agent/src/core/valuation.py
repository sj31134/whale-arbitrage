"""
Valuation Models: Decomposition, DCF, Shapley Bottleneck Rent, and Margin of Safety.
"""
import math
from typing import Dict, Any


class ValuationEngine:
    @staticmethod
    def calculate_land_building_decomposition(
        initial_land_value: float,
        initial_building_value: float,
        land_annual_growth_rate: float,
        building_depreciation_rate: float,
        years: int
    ) -> Dict[str, Any]:
        """
        V(t) = V_Land(0) * e^(g_land * t) + V_Building(0) * max(0, 1 - delta * t)
        Computes future value and the ratio of land vs total capital over time.
        """
        future_land_val = initial_land_value * math.exp(land_annual_growth_rate * years)
        depreciation_factor = max(0.0, 1.0 - (building_depreciation_rate * years))
        future_bldg_val = initial_building_value * depreciation_factor
        total_future_val = future_land_val + future_bldg_val
        land_dominance_ratio = future_land_val / total_future_val if total_future_val > 0 else 1.0

        return {
            "initial_total": initial_land_value + initial_building_value,
            "future_total": total_future_val,
            "future_land_value": future_land_val,
            "future_building_value": future_bldg_val,
            "land_dominance_ratio": land_dominance_ratio,
            "cagr": ((total_future_val / (initial_land_value + initial_building_value)) ** (1.0 / years)) - 1.0 if years > 0 else 0.0
        }

    @staticmethod
    def calculate_dcf_intrinsic_value(
        current_fcf: float,
        fcf_growth_rate: float,
        terminal_growth_rate: float,
        discount_rate: float,
        forecast_years: int = 5
    ) -> float:
        """
        Calculates 2-stage DCF intrinsic value.
        """
        if discount_rate <= terminal_growth_rate:
            raise ValueError("Discount rate must be strictly greater than terminal growth rate.")

        present_value = 0.0
        projected_fcf = current_fcf

        for t in range(1, forecast_years + 1):
            projected_fcf *= (1.0 + fcf_growth_rate)
            present_value += projected_fcf / ((1.0 + discount_rate) ** t)

        terminal_fcf = projected_fcf * (1.0 + terminal_growth_rate)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
        pv_terminal_value = terminal_value / ((1.0 + discount_rate) ** forecast_years)

        return present_value + pv_terminal_value

    @staticmethod
    def calculate_shapley_bottleneck_rent(
        ecosystem_total_value: float,
        substitutability_index: float,   # 0.0 (perfectly unique/SPOF) to 1.0 (easily commoditized)
        pricing_power_margin: float      # e.g., 0.50 (50% gross margin pricing power)
    ) -> float:
        """
        Estimates the economic rent captured by a critical bottleneck node (TSMC, ASML, Grid Transformers).
        Higher uniqueness (lower substitutability) + higher pricing power = greater captured surplus.
        """
        uniqueness_factor = 1.0 - min(max(substitutability_index, 0.0), 1.0)
        captured_rent = ecosystem_total_value * uniqueness_factor * pricing_power_margin
        return captured_rent

    @staticmethod
    def calculate_margin_of_safety(
        current_price: float,
        intrinsic_value: float
    ) -> float:
        """
        Margin of Safety (%) = (Intrinsic Value - Current Price) / Intrinsic Value
        Positive value indicates a discount (safety margin).
        """
        if intrinsic_value <= 0:
            return 0.0
        return (intrinsic_value - current_price) / intrinsic_value
