"""
Risk Manager: Manages portfolio risk, downside stress tests, and thesis invalidation triggers.
"""
from typing import List, Dict, Any
from ..core.asset import Asset


class RiskManager:
    def __init__(self, max_portfolio_drawdown: float = 0.20):
        self.max_portfolio_drawdown = max_portfolio_drawdown

    def stress_test_portfolio_bear_case(self, portfolio_allocation: List[Dict[str, Any]], asset_map: Dict[str, Asset]) -> Dict[str, Any]:
        """
        Calculates the portfolio return in a synchronized Bear Case catastrophe.
        """
        total_bear_loss = 0.0
        details = []

        for item in portfolio_allocation:
            asset = asset_map.get(item["asset_id"])
            if not asset:
                continue
            weight = item["recommended_weight_pct"]
            bear_ret = asset.scenarios.bear_case.expected_return_pct
            contribution = weight * bear_ret
            total_bear_loss += contribution
            details.append({
                "asset_id": asset.id,
                "asset_name": asset.name,
                "weight_pct": weight,
                "bear_loss_pct": bear_ret,
                "portfolio_impact_pct": contribution
            })

        return {
            "portfolio_bear_scenario_return_pct": total_bear_loss,
            "passes_max_drawdown_limit": abs(total_bear_loss) <= self.max_portfolio_drawdown,
            "asset_breakdown": details
        }

    def check_thesis_triggers(self, asset: Asset, current_events: List[str]) -> List[str]:
        """
        Detects if any recorded thesis invalidation triggers have been hit by current events.
        """
        breaches = []
        for trigger in asset.thesis_invalidation_triggers:
            for event in current_events:
                if any(word in event.lower() for word in trigger.lower().split()[:3]):
                    breaches.append(f"ALERT: Potential thesis invalidation for {asset.name} - Trigger: '{trigger}' vs Event: '{event}'")
        return breaches

    def multi_scenario_stress_test(self, portfolio_allocation: List[Dict[str, Any]], asset_map: Dict[str, Asset]) -> Dict[str, Any]:
        """
        Executes institutional 4-scenario stress testing across:
        1) Mean-Reversion Baseline (P=0.45)
        2) AI Credit Contagion & Stagflation (P=0.30)
        3) Extreme Black-Swan Liquidity Freeze (P=0.10)
        4) Winner-Takes-All Supercycle Boom (P=0.15)
        """
        scenarios = {
            "S1_Mean_Reversion": {"prob": 0.45, "returns": {"005935": 20.0, "GOOG": 12.0, "138040": 8.0, "009540": 15.0, "CASH": 0.0}},
            "S2_AI_Credit_Contagion": {"prob": 0.30, "returns": {"005935": -12.0, "GOOG": -5.0, "138040": 2.0, "009540": -8.0, "CASH": 0.0}},
            "S3_Black_Swan_Liquidity": {"prob": 0.10, "returns": {"005935": -25.0, "GOOG": -15.0, "138040": -8.0, "009540": -20.0, "CASH": 0.0}},
            "S4_Supercycle_Boom": {"prob": 0.15, "returns": {"005935": 50.0, "GOOG": 30.0, "138040": 25.0, "009540": 40.0, "CASH": 0.0}}
        }

        scenario_results = {}
        expected_portfolio_return = 0.0
        max_drawdown = 0.0

        for s_id, s_data in scenarios.items():
            s_return = 0.0
            for item in portfolio_allocation:
                aid = item["asset_id"]
                w = item["recommended_weight_pct"]
                # Match asset ticker or fallback to base
                ticker = aid.split("-")[-1] if "-" in aid else aid
                ret = s_data["returns"].get(ticker, s_data["returns"].get(aid, -10.0))
                s_return += w * ret

            scenario_results[s_id] = {
                "probability": s_data["prob"],
                "portfolio_return_pct": round(s_return, 2)
            }
            expected_portfolio_return += s_data["prob"] * s_return
            if s_return < max_drawdown:
                max_drawdown = s_return

        limit_pct = self.max_portfolio_drawdown * 100.0 if self.max_portfolio_drawdown < 1.0 else self.max_portfolio_drawdown
        return {
            "scenario_results": scenario_results,
            "expected_return_pct": round(expected_portfolio_return, 2),
            "max_drawdown_mdd_pct": round(max_drawdown, 2),
            "passes_max_drawdown_limit": abs(max_drawdown) <= limit_pct
        }

    def calculate_vol_targeting_liquidation(self, vkospi_index: float, target_vol_pct: float = 15.0) -> Dict[str, Any]:
        """
        Models the forced algorithmic de-risking triggered by VKOSPI / VIX volatility spikes.
        w_t = min(1.0, target_vol / current_vol)
        """
        current_vol = max(1.0, vkospi_index)
        forced_equity_weight = min(1.0, target_vol_pct / current_vol)
        forced_liquidation_pct = max(0.0, 1.0 - forced_equity_weight) * 100.0

        return {
            "vkospi_index": vkospi_index,
            "target_vol_pct": target_vol_pct,
            "forced_equity_weight_pct": round(forced_equity_weight * 100.0, 2),
            "forced_liquidation_pct": round(forced_liquidation_pct, 2),
            "regime": "EXTREME_FORCED_DERISKING" if vkospi_index >= 40.0 else "NORMAL_REGIME"
        }

    def evaluate_timing_regime(
        self,
        kospi_close: float,
        kospi_ma20: float,
        kospi_ma60: float,
        sox_close: float,
        sox_ma20: float,
        us_10y_yield_pct: float,
        vix_index: float,
        dxy_index: float,
        dxy_20d_ago: float,
        foreign_5d_net_krw_trillion: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Evaluates the 5-Factor Quantitative Timing & Foreign Flow Inflection Regime
        backtested across 2024-2026 bull ignition windows (2,293 -> 9,064) and bear crashes.
        Returns score (0-5), flow confirmation status, regime label, and cash deployment rule.
        """
        signals = {
            "kospi_trend_aligned": kospi_close > kospi_ma20 and kospi_ma20 > kospi_ma60,
            "sox_above_ma20": sox_close > sox_ma20,
            "us10y_below_ceiling": us_10y_yield_pct < 4.55,
            "vix_calm_regime": vix_index < 22.0,
            "dxy_liquidity_easing": dxy_index < 101.5 or dxy_index < dxy_20d_ago,
        }
        macro_trend_score = sum(1 for passed in signals.values() if passed)
        foreign_flow_confirmed = foreign_5d_net_krw_trillion > 0.5  # >+5,000억 5D rolling

        if macro_trend_score >= 4 and foreign_flow_confirmed:
            regime = "FULL_RISK_ON_IGNITION"
            action = "Deploy 100% strategic cash tranches into top-ranked Barbell Core/Satellite bottlenecks."
        elif macro_trend_score >= 4:
            regime = "MACRO_TAILWIND_AWAITING_FLOW"
            action = "Scale in 30-50% of dry powder; wait for 5-day foreign net buying > +0.5조 KRW."
        elif macro_trend_score >= 2:
            regime = "NEUTRAL_CHOP_TRANSITION"
            action = "Hold existing Core fortress; restrict buys strictly to >=25% Margin-of-Safety spikes."
        else:
            regime = "RISK_OFF_PRESERVATION"
            action = "Strict Buy Freeze on chase rallies; preserve cash buffer until Score >= 3 or 20MA reclaim."

        return {
            "macro_trend_score": macro_trend_score,
            "max_score": 5,
            "signals": signals,
            "foreign_5d_net_krw_trillion": round(foreign_5d_net_krw_trillion, 2),
            "foreign_flow_confirmed": foreign_flow_confirmed,
            "timing_regime": regime,
            "execution_directive": action,
        }

    def evaluate_algo_counter_edge(
        self,
        daily_drop_pct: float,
        intraday_rebound_from_low_pct: float,
        financial_inv_net_eok: float,
        foreign_net_eok: float,
        corporate_buyback_net_eok: float,
        ma20_disparity_pct: float,
        consecutive_drop_days: int = 1,
    ) -> Dict[str, Any]:
        """
        Reverse-engineers Program/ETF-LP arbitrage, VaR forced liquidation, and CTA exhaustion
        to detect counter-algorithmic entry traps vs genuine flash-liquidity edges.
        """
        lp_arb_trap = financial_inv_net_eok >= 8000.0 and foreign_net_eok <= -10000.0
        var_exhaustion = (
            daily_drop_pct <= -3.5
            and consecutive_drop_days >= 2
            and intraday_rebound_from_low_pct >= 2.0
        )
        cta_oversold_floor = ma20_disparity_pct <= -7.0 and corporate_buyback_net_eok >= 3000.0

        alerts = []
        if lp_arb_trap:
            alerts.append("ETF_LP_ARB_BOUNCE_TRAP: 금융투자 대규모 매수는 2~3일 내 기계적 재매도(Unwind) 유발 주의")
        if var_exhaustion:
            alerts.append("VAR_CLIMAX_REVERSAL_EDGE: 연속 급락 후 +2% 이상 아래꼬리 형성, 단기 평균회귀(T+5 승률 61.5%+) 구간")
        if cta_oversold_floor:
            alerts.append("CTA_EXHAUSTION_CORPORATE_FLOOR: 20MA 과매도(-7%↓) 구간 내 법인 자사주 비탄력 매수 방어 가동")

        edge_status = (
            "HIGH_CONVICTION_COUNTER_ALGO_BID" if (var_exhaustion and cta_oversold_floor and not lp_arb_trap)
            else "WAIT_LP_UNWIND_BEFORE_CHASE" if lp_arb_trap
            else "CTA_FLOOR_ACCUMULATION_ZONE" if cta_oversold_floor
            else "NO_ALGO_DISLOCATION"
        )

        return {
            "edge_status": edge_status,
            "lp_arb_trap_active": lp_arb_trap,
            "var_exhaustion_triggered": var_exhaustion,
            "cta_oversold_floor_active": cta_oversold_floor,
            "alerts": alerts,
        }
