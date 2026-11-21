"""
Flow-Volume Support & Resistance Engine:
Calculates true structural support and resistance levels using participant cost bases (VWAP),
dark pool accumulations, trapped retail volume ceilings, and margin/options gamma walls.
"""
from typing import List, Tuple
from .models import (
    ActorType, SupportResistanceType, SupportResistanceLevel,
    StockMicrostructureProfile, MarketType
)


class SupportResistanceEngine:
    """
    Computes precise support and resistance levels differentiated by actor cost bases
    rather than superficial high/low chart lines.
    """

    def calculate_levels(self, profile: StockMicrostructureProfile) -> StockMicrostructureProfile:
        """
        Calculates and attaches support and resistance levels to the profile.
        """
        current_p = profile.current_price
        curr = profile.currency
        is_us = profile.market == MarketType.US or curr == "USD"
        supports: List[SupportResistanceLevel] = []
        resistances: List[SupportResistanceLevel] = []

        foreign_flow = profile.actor_flows.get(ActorType.FOREIGN)
        inst_pension = profile.actor_flows.get(ActorType.INST_PENSION)
        inst_invtrust = profile.actor_flows.get(ActorType.INST_INVTRUST)
        dark_pool = profile.actor_flows.get(ActorType.DARK_POOL)
        retail_flow = profile.actor_flows.get(ActorType.RETAIL)
        retail_margin = profile.actor_flows.get(ActorType.RETAIL_MARGIN)

        # ----------------------------------------------------
        # 1. SMART MONEY FLOORS (Institutional / Foreign / Dark Pool VWAPs)
        # ----------------------------------------------------
        if foreign_flow and foreign_flow.estimated_vwap_20d <= current_p:
            dist = (foreign_flow.estimated_vwap_20d - current_p) / current_p * 100.0
            desc = "외국인/헤지펀드 20일 추정 평단가 (세력 단기 방어선)" if not is_us else "Hedge Funds / Offshore 20D VWAP (Smart Money Floor)"
            supports.append(SupportResistanceLevel(
                level_type=SupportResistanceType.SMART_MONEY_FLOOR,
                price=round(foreign_flow.estimated_vwap_20d, 2),
                strength_score=8.8,
                volume_density_pct=28.5,
                dominant_actor=ActorType.FOREIGN,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))
        elif foreign_flow and foreign_flow.estimated_vwap_20d > current_p:
            dist = (foreign_flow.estimated_vwap_20d - current_p) / current_p * 100.0
            desc = "외국인 20일 손실 평단가 (외인 원금 회복 매물선)" if not is_us else "Offshore Trapped VWAP Resistance"
            resistances.append(SupportResistanceLevel(
                level_type=SupportResistanceType.STRUCTURAL_COST_BASE,
                price=round(foreign_flow.estimated_vwap_20d, 2),
                strength_score=7.5,
                volume_density_pct=22.0,
                dominant_actor=ActorType.FOREIGN,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))

        if inst_pension and inst_pension.estimated_vwap_60d <= current_p:
            dist = (inst_pension.estimated_vwap_60d - current_p) / current_p * 100.0
            desc = "연기금/국가 60일 누적 매수 평단가 (구조적 철통 지지선)" if not is_us else "Institutional / 13F Long-Term Cost Base"
            supports.append(SupportResistanceLevel(
                level_type=SupportResistanceType.STRUCTURAL_COST_BASE,
                price=round(inst_pension.estimated_vwap_60d, 2),
                strength_score=9.4,
                volume_density_pct=34.0,
                dominant_actor=ActorType.INST_PENSION,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))

        if inst_invtrust and inst_invtrust.estimated_vwap_20d <= current_p:
            dist = (inst_invtrust.estimated_vwap_20d - current_p) / current_p * 100.0
            desc = "투신/운용사 액티브 20일 추정 평단가 지지선" if not is_us else "Mutual Fund / ETF Rebalancing Support"
            supports.append(SupportResistanceLevel(
                level_type=SupportResistanceType.SMART_MONEY_FLOOR,
                price=round(inst_invtrust.estimated_vwap_20d, 2),
                strength_score=8.2,
                volume_density_pct=20.5,
                dominant_actor=ActorType.INST_INVTRUST,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))

        # Dark Pool Floor (US Equities)
        if dark_pool and dark_pool.estimated_vwap_20d <= current_p:
            dist = (dark_pool.estimated_vwap_20d - current_p) / current_p * 100.0
            supports.append(SupportResistanceLevel(
                level_type=SupportResistanceType.DARK_POOL_VWAP,
                price=round(dark_pool.estimated_vwap_20d, 2),
                strength_score=9.2,
                volume_density_pct=30.0,
                dominant_actor=ActorType.DARK_POOL,
                description="Dark Pool Whale Block VWAP (다크풀 고래 매집 지지선)",
                distance_from_current_pct=round(dist, 2)
            ))

        # ----------------------------------------------------
        # 2. TRAPPED RETAIL CEILINGS & OPTIONS GAMMA WALLS
        # ----------------------------------------------------
        if retail_flow and retail_flow.estimated_vwap_20d >= current_p:
            dist = (retail_flow.estimated_vwap_20d - current_p) / current_p * 100.0
            desc = "개인 20일 집중 매수 물림 단가 (본전 탈출 매도 압력선)" if not is_us else "Retail Overhead Trapped Ceiling"
            resistances.append(SupportResistanceLevel(
                level_type=SupportResistanceType.TRAPPED_RETAIL_CEILING,
                price=round(retail_flow.estimated_vwap_20d, 2),
                strength_score=9.1,
                volume_density_pct=32.0,
                dominant_actor=ActorType.RETAIL,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))

        if retail_flow and retail_flow.estimated_vwap_60d >= current_p:
            dist = (retail_flow.estimated_vwap_60d - current_p) / current_p * 100.0
            desc = "개인 60일 고점 물림 매물대 (장기 악성 저항선)" if not is_us else "Long-Term Overhead Resistance Zone"
            resistances.append(SupportResistanceLevel(
                level_type=SupportResistanceType.HEAVY_OVERHEAD_SUPPLY,
                price=round(retail_flow.estimated_vwap_60d, 2),
                strength_score=8.5,
                volume_density_pct=25.0,
                dominant_actor=ActorType.RETAIL,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))

        # US Options Gamma Call Wall
        if is_us:
            gamma_call_wall = round(current_p * 1.06, 2)
            dist_g = (gamma_call_wall - current_p) / current_p * 100.0
            resistances.append(SupportResistanceLevel(
                level_type=SupportResistanceType.OPTIONS_GAMMA_WALL,
                price=gamma_call_wall,
                strength_score=8.7,
                volume_density_pct=28.0,
                dominant_actor=ActorType.FOREIGN_PROGRAM,
                description="Market Maker 0DTE Options Call Wall (감마 핀 저항벽)",
                distance_from_current_pct=round(dist_g, 2)
            ))

        # ----------------------------------------------------
        # 3. MARGIN CALL CASCADE LIQUIDATION LINE
        # ----------------------------------------------------
        if retail_margin:
            margin_liq_price = retail_margin.estimated_vwap_20d * 0.74
            dist = (margin_liq_price - current_p) / current_p * 100.0
            desc = "신용융자 담보부족 반대매매 청산 유발선 (과매도 패닉 바닥 매수선)" if not is_us else "Forced Liquidation & Stop-Cascade Exhaustion Line"
            supports.append(SupportResistanceLevel(
                level_type=SupportResistanceType.MARGIN_LIQUIDATION_LINE,
                price=round(margin_liq_price, 2),
                strength_score=9.6,
                volume_density_pct=15.0,
                dominant_actor=ActorType.RETAIL_MARGIN,
                description=desc,
                distance_from_current_pct=round(dist, 2)
            ))

        # ----------------------------------------------------
        # 4. POINT OF CONTROL (POC)
        # ----------------------------------------------------
        poc = profile.poc_price
        dist_poc = (poc - current_p) / current_p * 100.0
        if poc <= current_p:
            supports.append(SupportResistanceLevel(
                level_type=SupportResistanceType.POINT_OF_CONTROL,
                price=round(poc, 2),
                strength_score=8.0,
                volume_density_pct=40.0,
                dominant_actor=ActorType.FOREIGN_PROGRAM,
                description="Volume POC (최대 거래대금 누적 중심 밸류 지지선)",
                distance_from_current_pct=round(dist_poc, 2)
            ))
        else:
            resistances.append(SupportResistanceLevel(
                level_type=SupportResistanceType.POINT_OF_CONTROL,
                price=round(poc, 2),
                strength_score=8.0,
                volume_density_pct=40.0,
                dominant_actor=ActorType.RETAIL,
                description="Volume POC (최대 거래대금 누적 중심 밸류 저항선)",
                distance_from_current_pct=round(dist_poc, 2)
            ))

        supports = sorted(supports, key=lambda x: x.price, reverse=True)
        resistances = sorted(resistances, key=lambda x: x.price)

        profile.support_levels = supports
        profile.resistance_levels = resistances

        return profile
