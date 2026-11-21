"""
Investment Memo Generator: Formats professional Institutional Investment Committee Memos in Markdown.
"""
from typing import List, Dict, Any
from ..core.asset import Asset


class InvestmentMemoGenerator:
    @staticmethod
    def generate_asset_memo(asset: Asset) -> str:
        """
        Generates an in-depth institutional Investment Committee memo for a single asset.
        """
        scores = asset.skill_scores
        scenarios = asset.scenarios

        memo = rf"""# 🏛️ INSTITUTIONAL INVESTMENT COMMITTEE MEMORANDUM

**Asset ID:** `{asset.id}`  
**Asset Name:** **{asset.name}**  
**Asset Class:** `{asset.asset_class.value}`  
**Recommended Allocation Tier:** **{asset.tier.value}**  
**Current Price:** `${asset.current_price:,.2f}` | **Base Intrinsic Value:** `${asset.intrinsic_value_base:,.2f}`  
**Margin of Safety:** **{asset.margin_of_safety_pct * 100:.1f}%**

---

## 1. Executive Summary & Investment Thesis
* **The Core Premise:** {asset.moat_description}
* **Bottleneck Role:** {asset.bottleneck_role}
* **Composite Universal Skill Score:** **{scores.weighted_composite_score:.2f} / 10.0**
* **Expected Return \(E[R]\):** **+{scenarios.expected_return * 100:.1f}%** | **Payoff Ratio:** **{scenarios.payoff_ratio:.2f}x**

---

## 2. Universal 5 Skills Scorecard (Grade: 1 - 10)

| Skill # | Skill Name | Score | Analytical Justification & Evidence |
| :---: | :--- | :---: | :--- |
| **01** | **Asset Decomposition (Shell vs. Core)** | **{scores.decomposition_score:.1f}/10** | High proportion of non-depreciating, compounding core value over depreciating operational shell. |
| **02** | **Absolute Supply Inelasticity** | **{scores.inelasticity_score:.1f}/10** | Physical/structural impossibility of duplicating capacity even during sharp price spikes (\(E_s \approx 0\)). |
| **03** | **Price-Inelastic Buyer Cohort** | **{scores.buyer_quality_score:.1f}/10** | Demand backed by cash-rich UHNWI, central banks, or mission-critical enterprise budgets. |
| **04** | **Walled Garden & Privacy Moat** | **{scores.walled_garden_score:.1f}/10** | Exclusive, closed ecosystem providing extreme security, privacy, and proprietary lock-in. |
| **05** | **Spillover Arbitrage** | **{scores.spillover_score:.1f}/10** | Free-riding on massive external infrastructure Capex without bearing the development debt/costs. |

**Weighted Composite Score:** `{scores.weighted_composite_score:.2f} / 10.0`

---

## 3. Probabilistic 3-Stage Scenario Model & Payoff Asymmetry

$$E[R] = (0.30 \times R_{{\text{{Bull}}}}) + (0.50 \times R_{{\text{{Base}}}}) + (0.20 \times R_{{\text{{Bear}}}})$$

| Scenario | Prob | Target Price | Return (%) | Key Catalyst / Operational Driver |
| :--- | :---: | :---: | :---: | :--- |
| **Bull Case** | **30%** | `${scenarios.bull_case.target_price:,.2f}` | **+{scenarios.bull_case.expected_return_pct * 100:.1f}%** | {scenarios.bull_case.catalyst_description} |
| **Base Case** | **50%** | `${scenarios.base_case.target_price:,.2f}` | **+{scenarios.base_case.expected_return_pct * 100:.1f}%** | {scenarios.base_case.catalyst_description} |
| **Bear Case** | **20%** | `${scenarios.bear_case.target_price:,.2f}` | **{scenarios.bear_case.expected_return_pct * 100:.1f}%** | {scenarios.bear_case.catalyst_description} |

* **Expected Return \(E[R]\):** `+{scenarios.expected_return * 100:.1f}%`
* **Convexity Payoff Ratio (Bull / |Bear|):** `{scenarios.payoff_ratio:.2f}x` (Threshold \(\ge 3.0x\): {'✅ PASS' if scenarios.payoff_ratio >= 3.0 else '❌ FAIL'})

---

## 4. Downside Risk & Thesis Invalidation Triggers

The following events constitute a structural violation of the core thesis and require **immediate position liquidation**:
"""
        for i, trigger in enumerate(asset.thesis_invalidation_triggers, 1):
            memo += f"\n- **Trigger {i}:** {trigger}"

        memo += f"""

---

## 5. Committee Verdict & Allocation Recommendation
* **Decision:** **{'APPROVED FOR PORTFOLIO INCLUSION' if asset.is_investable else 'REJECTED / WATCHLIST ONLY'}**
* **Bucket:** **{asset.tier.value}**
* **Target Sizing:** **{asset.recommended_weight_pct * 100:.1f}% of Total Portfolio**
"""
        return memo

    @staticmethod
    def generate_portfolio_memo(portfolio_data: Dict[str, Any]) -> str:
        """
        Generates a summary portfolio allocation report.
        """
        allocated = portfolio_data.get("allocated_assets", [])
        memo = rf"""# 🌐 MASTER BARBELL PORTFOLIO ALLOCATION REPORT

**Overall Expected Return \(E[R]\):** **+{portfolio_data.get('portfolio_expected_return_pct', 0.0) * 100:.2f}%**  
**Core Bucket Weight (Target 60~70%):** **{portfolio_data.get('core_weight_total', 0.0) * 100:.1f}%**  
**Satellite Bucket Weight (Target 30~40%):** **{portfolio_data.get('satellite_weight_total', 0.0) * 100:.1f}%**  
**Cash Reserve Buffer:** **{portfolio_data.get('cash_buffer_weight', 0.0) * 100:.1f}%**

---

### Active Holdings Breakdown

| Asset ID | Name | Class | Tier | Weight (%) | Exp. Return | Payoff | Score (/10) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
"""
        for item in allocated:
            memo += f"| `{item['asset_id']}` | **{item['asset_name']}** | {item['asset_class']} | `{item['tier']}` | **{item['recommended_weight_pct']*100:.1f}%** | +{item['expected_return_pct']*100:.1f}% | {item['payoff_ratio']:.1f}x | {item['composite_score']:.2f} |\n"

        memo += """
---
### Dynamic Execution Guidelines:
1. **Satellite Rerating Harvest:** Once any Satellite position expands by >150% (+2.5x original), automatically trigger 50% profit realization into Core geographic and hard monetary anchors.
2. **Margin of Safety Guardrail:** No purchases executed unless current price reflects >= 15% discount to Base Intrinsic Value.
3. **5-Factor Quantitative Timing & Foreign Flow Gate:** Deploy aggressive dry powder only when Macro/Trend Timing Score >= 4/5 (`KOSPI > 20MA > 60MA`, `SOX > 20MA`, `US10Y < 4.55%`, `VIX < 22`, `DXY < 101.5 or falling 20D`) AND 5-day rolling foreign net buying turns > +0.5조 KRW.
"""
        return memo
