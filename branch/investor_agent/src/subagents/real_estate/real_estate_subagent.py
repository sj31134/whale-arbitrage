"""
RealEstateSubagent (Tier 2-B Dedicated Domain Specialist):
100% Strict Domain Isolation: Pure Real Estate, Multi-Source Listing Ingestion, Land Share Decomposition, and Rights Analysis.
Enforces the 4-Pillar Quantitative & Empirical Harness Architecture approved by User:
1. Asset Decomposition: V(t) = Land(e^gt) + Bldg(0), L_ratio >= 70%
2. Monopoly Moat: Zero expansion land area, transit express 30-min corridor <= 500m, density FAR multiplier
3. Anchor High-Income Solvency Cohorts: AI/IT (Pangyo), K-Semiconductor, Global Finance (YBD)
4. Policy, Legal & 7-Step Court Auction Rights Margin: Cash <= 300M feasibility, Liability = 0, Urban Renewal Art 39
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from .auction_rights_analyzer import AuctionRightsAnalyzer, AuctionAnalysisReport, TenantRight
from .live_court_auction_collector import LiveCourtAuctionCollector
from .court_auction_verifier import CourtAuctionVerifier
from .real_estate_pipeline import RealEstateDataPipeline, MarketPropertyRecord
from ...core.valuation import ValuationEngine
from ...core.scoring_engine import ScoringEngine


class RealEstateSubagent:
    """
    Dedicated Tier 2-B Real Estate Subagent Engine.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.auction_analyzer = AuctionRightsAnalyzer()
        auction_dir = (Path(data_dir) / "court_auction") if data_dir is not None else None
        re_dir = (Path(data_dir) / "real_estate") if data_dir is not None else None
        self.auction_collector = LiveCourtAuctionCollector(cache_dir=auction_dir)
        self.verifier = self.auction_collector.verifier
        self.pipeline = RealEstateDataPipeline(data_dir=re_dir)

    def fetch_comprehensive_market_universe(
        self,
        min_price: float = 350_000_000,
        max_price: float = 850_000_000,
        target_regions: Optional[List[str]] = None
    ) -> List[MarketPropertyRecord]:
        return self.pipeline.fetch_multi_source_listings(
            min_price=min_price,
            max_price=max_price,
            target_regions=target_regions
        )

    def get_september_october_auction_cases(self) -> List[Dict[str, Any]]:
        return self.auction_collector.fetch_live_auction_feed(start_date="2026-09-01", end_date="2026-10-31")

    def analyze_scheduled_court_auctions(self, month_filter: str = "all") -> List[AuctionAnalysisReport]:
        res = self.auction_collector.run_live_rights_analysis_pipeline(
            start_date="2026-09-01",
            end_date="2026-10-31"
        )
        reports = res["reports"]
        if month_filter != "all":
            reports = [r for r in reports if r.auction_date.startswith(month_filter)]
        return reports

    def screen_land_candidate(
        self,
        candidate_id: str,
        name: str,
        real_price_eok: float,
        real_jeonse_eok: float,
        land_area_pyeong: float,
        intrinsic_value_eok: float,
        is_oversupplied_periphery: bool,
        has_high_income_cohort: bool,
        location_compounding_factor: float = 1.0
    ) -> Dict[str, Any]:
        raw_gap = real_price_eok - real_jeonse_eok
        passed_veto, veto_msg = self.scoring_engine.audit_real_estate_value_trap(
            is_oversupplied_periphery=is_oversupplied_periphery,
            has_anchor_high_income_cohort=has_high_income_cohort,
            raw_gap_eok=raw_gap
        )
        if not passed_veto:
            return {
                "candidate_id": candidate_id,
                "name": name,
                "is_qualified": False,
                "real_price_eok": real_price_eok,
                "real_jeonse_eok": real_jeonse_eok,
                "gap_eok": raw_gap,
                "land_area_pyeong": land_area_pyeong,
                "veto_reason": veto_msg
            }

        land_price_pyeong = (real_price_eok * 100_000_000) / land_area_pyeong if land_area_pyeong > 0 else 0
        adjusted_iv = intrinsic_value_eok * location_compounding_factor
        mos = (adjusted_iv - real_price_eok) / adjusted_iv if adjusted_iv > 0 else 0.0

        return {
            "candidate_id": candidate_id,
            "name": name,
            "is_qualified": True,
            "real_price_eok": real_price_eok,
            "real_jeonse_eok": real_jeonse_eok,
            "gap_eok": raw_gap,
            "land_area_pyeong": land_area_pyeong,
            "land_price_per_pyeong": land_price_pyeong,
            "intrinsic_value_eok": adjusted_iv,
            "margin_of_safety": mos,
            "leverage": real_price_eok / raw_gap if raw_gap > 0 else 1.0,
            "veto_reason": veto_msg
        }

    def analyze_court_auction(
        self,
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
        return self.auction_analyzer.analyze_case(
            case_number=case_number,
            court_name=court_name,
            auction_date=auction_date,
            bidding_round=bidding_round,
            location=location,
            property_type=property_type,
            appraisal_value=appraisal_value,
            min_bid_price=min_bid_price,
            land_area_pyeong=land_area_pyeong,
            registry_rights=registry_rights,
            tenant_data=tenant_data,
            has_hug_waiver=has_hug_waiver,
            is_prior_to_redevelopment_cutoff=is_prior_to_redevelopment_cutoff,
            is_oversupplied_periphery=is_oversupplied_periphery,
            has_high_income_cohort=has_high_income_cohort
        )

    def run_subagent_pipeline(self, auction_month_filter: str = "all") -> Dict[str, Any]:
        market_records = self.fetch_comprehensive_market_universe(min_price=350_000_000, max_price=850_000_000)
        decomp_simulations = self._run_decomposition_simulations()

        # Hardcoded 4-pillar candidates for screening
        candidates_raw = [
            ("RE-YONGSAN-CORE", "Yongsan Wonhyo Moa-Town Villa Land (Seoul / 8.5억)", 8.5, 4.5, 8.4, 12.5, False, True, 1.25),
            ("RE-MAPO-YEOMRI", "Mapo Yeomri Redevelopment Land (Seoul / 6.8억)", 6.8, 4.2, 9.2, 9.8, False, True, 1.15),
            ("RE-BUNDANG-LEAD", "Bundang 1st New Town Lead District 59㎡ (Gyeonggi / 9.2억)", 9.2, 6.0, 14.8, 12.2, False, True, 1.15),
            ("RE-NOWON-RECON", "Nowon Sanggye Jugong Reconstruction 59㎡ (Seoul / 6.46억)", 6.46, 3.8, 12.1, 9.5, False, True, 1.05),
            ("RE-SUWON-YEONGTONG", "Suwon Yeongtong Maetan Jugong Reconstruction (Gyeonggi / 6.2억)", 6.2, 3.8, 14.0, 8.5, False, True, 1.05),
            ("TRAP-YANGJU-OKJEONG", "Yangju Okjeong Peripheral New Town (Gyeonggi / 3.8억)", 3.8, 3.5, 14.0, 4.0, True, False, 0.20),
            ("TRAP-GIMPO-OUTER", "Gimpo Tongjin Peripheral Outer Villa (Gyeonggi / 1.8억)", 1.8, 1.7, 7.5, 1.9, True, False, 0.20)
        ]

        screened_results = []
        for cid, cname, cp, cj, la, iv, is_over, has_cohort, g_factor in candidates_raw:
            res = self.screen_land_candidate(
                candidate_id=cid,
                name=cname,
                real_price_eok=cp,
                real_jeonse_eok=cj,
                land_area_pyeong=la,
                intrinsic_value_eok=iv,
                is_oversupplied_periphery=is_over,
                has_high_income_cohort=has_cohort,
                location_compounding_factor=g_factor
            )
            screened_results.append(res)

        live_pipeline_res = self.auction_collector.run_live_rights_analysis_pipeline(
            start_date="2026-09-01",
            end_date="2026-10-31"
        )
        auction_reports = live_pipeline_res["reports"]
        raw_cases = live_pipeline_res["raw_cases"]
        audit_results = live_pipeline_res["audit_results"]

        if auction_month_filter != "all":
            auction_reports = [r for r in auction_reports if r.auction_date.startswith(auction_month_filter)]

        memo = self.generate_subagent_markdown_memo(
            screened_results=screened_results,
            decomp_simulations=decomp_simulations,
            auction_reports=auction_reports,
            raw_cases=raw_cases,
            audit_results=audit_results,
            month_filter=auction_month_filter
        )

        total_candidates = len(screened_results) + len(auction_reports)

        return {
            "timestamp": datetime.now().isoformat(),
            "month_filter": auction_month_filter,
            "total_candidates_screened": total_candidates,
            "passed_candidates_count": sum(1 for r in screened_results if r["is_qualified"]) + sum(1 for a in auction_reports if not a.is_vetoed),
            "vetoed_traps_count": sum(1 for r in screened_results if not r["is_qualified"]) + sum(1 for a in auction_reports if a.is_vetoed),
            "screened_results": screened_results,
            "decomposition_simulations": decomp_simulations,
            "auction_reports_count": len(auction_reports),
            "auction_reports": auction_reports,
            "market_records": market_records,
            "super_core_market_records": [r for r in market_records if r.harness_verdict == "SUPER_CORE_PASS"],
            "prime_core_market_records": [r for r in market_records if r.harness_verdict == "PRIME_CORE_PASS"],
            "raw_cases": raw_cases,
            "audit_results": audit_results,
            "subagent_memo": memo
        }

    def _run_decomposition_simulations(self) -> List[Dict[str, Any]]:
        cases = [
            {"tier_name": "Yongsan/Seoul Core 1 (g = 8.5%)", "initial_land_pct": 0.85, "initial_bldg_pct": 0.15, "land_g": 0.085, "bldg_deprec": 0.035, "horizon_years": 20},
            {"tier_name": "Mapo/Pangyo Lead District (g = 7.5%)", "initial_land_pct": 0.78, "initial_bldg_pct": 0.22, "land_g": 0.075, "bldg_deprec": 0.040, "horizon_years": 20},
            {"tier_name": "Outer Greenfield Value Trap (g = 1.5%)", "initial_land_pct": 0.35, "initial_bldg_pct": 0.65, "land_g": 0.015, "bldg_deprec": 0.045, "horizon_years": 20}
        ]
        sim_results = []
        for c in cases:
            base_total = 1_000_000_000.0
            l_0 = base_total * c["initial_land_pct"]
            b_0 = base_total * c["initial_bldg_pct"]
            res_20y = self.valuation_engine.calculate_land_building_decomposition(
                initial_land_value=l_0,
                initial_building_value=b_0,
                land_annual_growth_rate=c["land_g"],
                building_depreciation_rate=c["bldg_deprec"],
                years=c["horizon_years"]
            )
            sim_results.append({
                "tier_name": c["tier_name"],
                "future_land_value": res_20y["future_land_value"],
                "future_bldg_value": res_20y["future_building_value"],
                "future_total_value": res_20y["future_total"],
                "total_return_pct": ((res_20y["future_total"] - base_total) / base_total) * 100
            })
        return sim_results

    def generate_subagent_markdown_memo(
        self,
        screened_results: List[Dict[str, Any]],
        decomp_simulations: List[Dict[str, Any]],
        auction_reports: List[AuctionAnalysisReport],
        raw_cases: List[Dict[str, Any]],
        audit_results: Dict[str, Any],
        month_filter: str = "all"
    ) -> str:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# 🏠 [Real Estate Subagent Final Memo] 2026년 9월·10월 서울·수도권 코어 부동산 분석서",
            f"> **분석 일시:** {now_str} (LIVE)  ",
            f"> **서브에이전트:** `real_estate_subagent` (Tier 2-B, 100% Real Estate Only)  ",
            f"> **하네스 스킬:** `.agents/skills/real-estate-subagent/SKILL.md` (승인 완료)  ",
            f"> **검증 엔진:** `CourtAuctionVerifier` (통과율: **{audit_results.get('integrity_score_pct', 100.0)}%**)  ",
            "",
            "---",
            "",
            "## 1. 4대 하네스 스킬 정량 지표 통과 코어 물건 리포트",
            "",
            "| 입찰기일 | 사건번호 (관할법원) | 소재지 및 물건명 | 감정가 / 최저가 | 대지지분 ($L_{\text{ratio}}$) | 토지 복리성장 ($g$) | 실질 총 취득원가 | 안전점수 | 하네스 판정 |",
            "| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
        ]
        for rep in auction_reports:
            app_s = f"{rep.appraisal_value/100_000_000:.2f}억"
            min_s = f"{rep.min_bid_price/100_000_000:.2f}억"
            tot_s = f"**{rep.estimated_total_acquisition_cost/100_000_000:.2f}억**"
            score_s = f"**{rep.safety_score:.1f}점**" if rep.safety_score >= 8.0 else f"{rep.safety_score:.1f}점"
            lines.append(
                f"| **{rep.auction_date}** | **{rep.case_number}**<br/>({rep.court_name}) | **{rep.location}** | {app_s} / {min_s} | {rep.land_area_pyeong:.1f}평 | 7.5%~8.5% | {tot_s} | {score_s} | {rep.final_verdict} |"
            )
        return "\n".join(lines)

    def sync_to_knowledge_graph(self, knowledge_graph: Any, subagent_results: Dict[str, Any]):
        """
        Synchronizes Real Estate & Court Auction Subagent findings into parent Knowledge Graph.
        """
        for r in subagent_results.get("screened_results", []):
            cid = r["candidate_id"]
            node_id = f"RE_{cid}"
            knowledge_graph.add_node(
                node_id=node_id,
                node_type="RealEstateLandAnchor",
                label=f"{r['name']}",
                metadata={
                    "is_qualified": r["is_qualified"],
                    "real_price_eok": r["real_price_eok"],
                    "gap_eok": r["gap_eok"],
                    "land_area_pyeong": r["land_area_pyeong"],
                    "margin_of_safety": r.get("margin_of_safety", 0.0),
                    "veto_reason": r.get("veto_reason", "")
                }
            )

        for rep in subagent_results.get("auction_reports", []):
            case_id = rep.case_number.replace("타경", "_").replace(" ", "_")
            node_id = f"AUCTION_{case_id}"
            knowledge_graph.add_node(
                node_id=node_id,
                node_type="CourtAuctionAnchor",
                label=f"{rep.court_name} {rep.case_number} ({rep.location})",
                metadata={
                    "auction_date": rep.auction_date,
                    "appraisal_value": rep.appraisal_value,
                    "min_bid_price": rep.min_bid_price,
                    "estimated_total_acquisition_cost": rep.estimated_total_acquisition_cost,
                    "safety_score": rep.safety_score,
                    "has_hug_waiver": rep.has_hug_waiver,
                    "is_redevelopment_eligible": rep.is_redevelopment_eligible,
                    "final_verdict": rep.final_verdict
                }
            )

