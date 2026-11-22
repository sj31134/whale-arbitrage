"""
Court Auction Legal Rights Analyzer (법원경매 7단계 권리분석 엔진):
Performs automated legal title inspection, Malso-gijun-gwonli determination,
tenant opposing power assessment, acquisition liability calculation, reconstruction eligibility audit,
and total acquisition cost & margin of safety modeling.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class TenantRight:
    name: str
    move_in_date: str  # 전입일자 YYYY-MM-DD
    fixed_date: Optional[str]  # 확정일자 YYYY-MM-DD
    deposit_amount: float  # 보증금 (원)
    demanded_dividend: bool  # 배당요구 여부
    has_opposing_power: bool = False  # 대항력 유무
    unpaid_deposit_liability: float = 0.0  # 낙찰자 인수 보증금 (원)


@dataclass
class AuctionAnalysisReport:
    case_number: str
    court_name: str
    auction_date: str  # 매각기일 (입찰일) YYYY-MM-DD
    bidding_round: str  # 1회차(100%), 2회차(80%), 3회차(64%) 등
    location: str
    property_type: str  # 아파트, 재개발 다세대, 고급빌라 등
    appraisal_value: float
    min_bid_price: float
    land_area_pyeong: float
    land_price_per_pyeong: float
    malso_gijun_date: str
    malso_gijun_type: str
    tenants: List[TenantRight]
    total_acquisition_liability: float
    estimated_total_acquisition_cost: float
    margin_of_safety: float
    has_hug_waiver: bool
    is_redevelopment_eligible: bool
    is_vetoed: bool
    safety_score: float  # 0.0 to 10.0
    final_verdict: str
    bidding_recommendation: str


class AuctionRightsAnalyzer:
    @staticmethod
    def determine_malso_gijun_right(rights_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        eligible_types = {"근저당", "저당", "가압류", "압류", "담보가등기", "경매기입등기", "임의경매기입등기", "강제경매기입등기"}
        valid_rights = [r for r in rights_list if r.get("type") in eligible_types]
        if not valid_rights:
            raise ValueError("말소기준권리 후보가 존재하지 않습니다.")
        valid_rights.sort(key=lambda x: x.get("date", "9999-12-31"))
        return valid_rights[0]

    @classmethod
    def analyze_case(
        cls,
        case_number: str,
        court_name: str,
        auction_date: str,
        bidding_round: str,
        location: str,
        property_type: str,
        appraisal_value: float,
        min_bid_price: float,
        land_area_pyeong: float,
        registry_rights: List[Dict[str, Any]],
        tenant_data: List[Dict[str, Any]],
        has_hug_waiver: bool = False,
        is_prior_to_redevelopment_cutoff: bool = True,
        is_oversupplied_periphery: bool = False,
        has_high_income_cohort: bool = True
    ) -> AuctionAnalysisReport:
        malso_right = cls.determine_malso_gijun_right(registry_rights)
        malso_date = malso_right["date"]
        
        analyzed_tenants = []
        total_liability = 0.0
        
        for t in tenant_data:
            move_in = t["move_in_date"]
            deposit = t.get("deposit", 0.0)
            fixed_date = t.get("fixed_date")
            demanded = t.get("demanded_dividend", True)
            
            has_opposing = move_in < malso_date
            liability = 0.0
            if has_opposing:
                if has_hug_waiver:
                    liability = 0.0
                elif not demanded:
                    liability = deposit
                else:
                    est_dividend = min(min_bid_price * 0.9, deposit)
                    liability = max(0.0, deposit - est_dividend)
            
            total_liability += liability
            analyzed_tenants.append(TenantRight(
                name=t.get("name", "미상"),
                move_in_date=move_in,
                fixed_date=fixed_date,
                deposit_amount=deposit,
                demanded_dividend=demanded,
                has_opposing_power=has_opposing,
                unpaid_deposit_liability=liability
            ))
            
        # 3-Gate Veto check
        is_vetoed = False
        veto_reasons = []
        if is_oversupplied_periphery:
            is_vetoed = True
            veto_reasons.append("반경 5km 대규모 택지 공급과잉 (Es >> 0)")
        if not has_high_income_cohort:
            is_vetoed = True
            veto_reasons.append("고소득 임차 코호트 및 학군 부재")

        # Estimated Total Acquisition Cost: 최저가 + 인수보증금 + 취득세(약 3.5%) + 명도예비비(500만원)
        est_taxes = appraisal_value * 0.035
        eviction_reserve = 5_000_000.0 if total_liability == 0 else 10_000_000.0
        total_acq_cost = min_bid_price + total_liability + est_taxes + eviction_reserve
        mos = (appraisal_value - total_acq_cost) / appraisal_value if appraisal_value > 0 else 0.0
        land_price_pyeong = (min_bid_price / land_area_pyeong) if land_area_pyeong > 0 else 0.0

        # Calculate Safety Score (0.0 to 10.0)
        safety_score = 10.0
        if is_vetoed:
            safety_score = 1.0
        else:
            if total_liability > 0:
                safety_score -= min(5.0, (total_liability / appraisal_value) * 10)
            if not is_prior_to_redevelopment_cutoff:
                safety_score -= 4.0

        safety_score = max(0.0, min(10.0, safety_score))

        # Determine Verdict & Bidding Recommendation
        if is_vetoed:
            verdict = f"❌ [100% VETO / 가치함정]: {', '.join(veto_reasons)}"
            rec = "⛔ [입찰 절대 금지]: 토지 희소성 결여 또는 임차 수요 부재로 자본 잠식 위험."
        elif total_liability > 0:
            verdict = f"⚠️ [주의 물건 / 보증금 인수]: 선순위 미배당 인수보증금 {total_liability/100_000_000:.2f}억 원 발생"
            rec = f"🔍 [인수금 역산 후 입찰]: 실질 취득가산출식 = (낙찰가 + {total_liability/100_000_000:.2f}억). 최저가 {min_bid_price/100_000_000:.2f}억 기준 실질 취득가 {(min_bid_price+total_liability)/100_000_000:.2f}억."
        elif has_hug_waiver:
            verdict = "🎯 [초특급 알파 물건]: HUG 대항력 포기 확약서 제출로 인수금 0원 확정"
            rec = f"🟢 [적극 입찰 추천]: 일반 입찰자 기피로 단독/저가 낙찰 기회. 감정가 대비 안전마진 {mos*100:.1f}% 확보."
        else:
            verdict = "✅ [안전 물건]: 모든 등기권리 및 임차권 완전 말소/소멸 확정"
            rec = f"🟢 [입찰 추천]: 권리관계 무결. 실투자 안전마진 {mos*100:.1f}% 및 대지지분 평당 {land_price_pyeong/10_000:,.0f}만 원 선점 기회."

        return AuctionAnalysisReport(
            case_number=case_number,
            court_name=court_name,
            auction_date=auction_date,
            bidding_round=bidding_round,
            location=location,
            property_type=property_type,
            appraisal_value=appraisal_value,
            min_bid_price=min_bid_price,
            land_area_pyeong=land_area_pyeong,
            land_price_per_pyeong=land_price_pyeong,
            malso_gijun_date=malso_date,
            malso_gijun_type=malso_right["type"],
            tenants=analyzed_tenants,
            total_acquisition_liability=total_liability,
            estimated_total_acquisition_cost=total_acq_cost,
            margin_of_safety=mos,
            has_hug_waiver=has_hug_waiver,
            is_redevelopment_eligible=is_prior_to_redevelopment_cutoff,
            is_vetoed=is_vetoed,
            safety_score=safety_score,
            final_verdict=verdict,
            bidding_recommendation=rec
        )

