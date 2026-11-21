"""
Scoring Engine: Implements the 5 Universal Investment Skills, 4 Fundamental Criteria,
and strict Valuation & Entry Price Hurdle Gates (Margin of Safety Gate).
"""
from typing import Dict, Any, Tuple
from .asset import UniversalSkillScores, AssetTier, AssetClass


class ScoringEngine:
    @staticmethod
    def evaluate_universal_skills(
        decomposition_score: float,
        inelasticity_score: float,
        buyer_quality_score: float,
        walled_garden_score: float,
        spillover_score: float
    ) -> UniversalSkillScores:
        """
        Creates and normalizes UniversalSkillScores.
        """
        return UniversalSkillScores(
            decomposition_score=min(max(decomposition_score, 0.0), 10.0),
            inelasticity_score=min(max(inelasticity_score, 0.0), 10.0),
            buyer_quality_score=min(max(buyer_quality_score, 0.0), 10.0),
            walled_garden_score=min(max(walled_garden_score, 0.0), 10.0),
            spillover_score=min(max(spillover_score, 0.0), 10.0)
        )

    @staticmethod
    def classify_asset_tier(
        asset_class: AssetClass,
        composite_score: float,
        payoff_ratio: float,
        margin_of_safety: float,
        is_hard_anchor_or_land: bool = False
    ) -> Tuple[AssetTier, str]:
        """
        Determines whether an asset qualifies for Core (60-70%), Satellite (30-40%), or Unqualified.
        STRICT ENTRY PRICE GATE: Assets without adequate Margin of Safety (MOS < 15%) are rejected.
        """
        # 1. Strict Valuation Hurdle (Cannot enter if current price is overvalued / MOS < 15%)
        if margin_of_safety < 0.15:
            return (
                AssetTier.UNQUALIFIED,
                f"❌ [진입 거부 / 고평가]: 현재 진입 가격이 고평가 상태임 (안전마진 {margin_of_safety*100:.1f}% < 기준 15.0%). 가격 조정 전까지 매수 금지."
            )

        # 2. Minimum Moat & Payoff Hurdle
        if composite_score < 6.5 or payoff_ratio < 2.5:
            return (
                AssetTier.UNQUALIFIED,
                f"❌ [진입 거부 / 해자 부족]: 종합 해자점수({composite_score:.1f}) 또는 손익비({payoff_ratio:.1f}x)가 기준 미달."
            )

        # 3. Core Qualification (High Moat + Deep Margin of Safety >= 20%)
        if is_hard_anchor_or_land and composite_score >= 8.0 and margin_of_safety >= 0.20:
            return (
                AssetTier.CORE,
                f"🏆 [CORE 선정]: 대체 불가능한 지리적/실물 대지 독점이며 두터운 안전마진({margin_of_safety*100:.1f}%) 확보."
            )

        if composite_score >= 8.0 and margin_of_safety >= 0.25 and payoff_ratio >= 3.0:
            return (
                AssetTier.CORE,
                f"🏆 [CORE 선정]: 최상위 경제적 해자(점수 {composite_score:.1f}) 및 극단적 저평가 안전마진({margin_of_safety*100:.1f}%) 확보."
            )

        # 4. Satellite Qualification (High Convexity + Adequate MOS >= 15%)
        if composite_score >= 7.5 and payoff_ratio >= 3.0 and margin_of_safety >= 0.15:
            return (
                AssetTier.SATELLITE,
                f"💎 [SATELLITE 선정]: 비대칭 상방 잠재력(손익비 {payoff_ratio:.1f}x) 및 적정 안전마진({margin_of_safety*100:.1f}%) 확보."
            )

        if composite_score >= 7.0 and margin_of_safety >= 0.20:
            return (
                AssetTier.SATELLITE,
                f"💎 [SATELLITE 선정]: 견고한 해자 및 안정적 안전마진({margin_of_safety*100:.1f}%) 확보."
            )

        return AssetTier.UNQUALIFIED, "종합 확신도 미달로 포트폴리오 편입 제외."

    @staticmethod
    def audit_real_estate_value_trap(
        is_oversupplied_periphery: bool,
        has_anchor_high_income_cohort: bool,
        raw_gap_eok: float
    ) -> Tuple[bool, str]:
        """
        Hard Veto Gate for Real Estate to prevent Value Traps (e.g. infinite supply periphery like Yangju).
        Returns (is_passed, reason_string).
        """
        # Gate 1: Supply Inelasticity Audit (Es approx 0)
        if is_oversupplied_periphery:
            return (
                False,
                r"❌ [100% VETO / 가치 함정]: 반경 5km 내 대규모 신도시/택지 공급 과잉 ($E_s \gg 0$). 토지 희소성 결여로 코어 선정 불가."
            )

        # Gate 2: High-Income Cohort Audit
        if not has_anchor_high_income_cohort:
            return (
                False,
                "❌ [100% VETO / 코호트 부재]: 고소득 대기업/3대 도심 30분 직결 일자리 또는 명문 학군가 배후 부재. 불황 시 역전세 취약."
            )

        return (True, "✅ [게이트 통과]: 공급 비탄력성 ($E_s \approx 0$) 및 고소득 영구 임차 코호트 검증 완료.")

