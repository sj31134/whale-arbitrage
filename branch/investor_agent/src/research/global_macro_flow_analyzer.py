"""
Global Macro Flow Analyzer: Deep-dive analysis on global money flows, commodities,
energy bottlenecks, critical materials, and regional economies with live price ingestion.
"""
from typing import Dict, List, Any
from ..core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from ..core.valuation import ValuationEngine
from ..core.scoring_engine import ScoringEngine
from ..data_pipeline.live_price_service import LivePriceService


class GlobalMacroFlowAnalyzer:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_global_macro_assets(self) -> List[Asset]:
        """
        Assets directly tied to global commodity flows, energy bottlenecks, critical materials,
        and macro infrastructure value chains.
        """
        assets: List[Asset] = []

        # 1. BHP Group (BHP / ASX: BHP) - Tier: CORE (Australia Resource Monopoly)
        p_bhp = self.price_service.get_price("MACRO-BHP", 86.78)
        iv_bhp = p_bhp * 1.25
        bhp_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.5, inelasticity_score=9.4, buyer_quality_score=9.2, walled_garden_score=9.3, spillover_score=9.5
        )
        assets.append(Asset(
            id="MACRO-BHP",
            name="BHP Group Limited (ASX: BHP / NYSE: BHP)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_bhp,
            intrinsic_value_base=iv_bhp,
            tier=AssetTier.CORE,
            skill_scores=bhp_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_bhp * 1.48, expected_return_pct=0.48, catalyst_description="구리 쇼티지 심화 및 중국 인프라 부양책 효과"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_bhp, expected_return_pct=0.25, catalyst_description="연 6-7% 배당수익률 지속 및 필바라 철광석/에스콘디다 구리 현금창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_bhp * 0.85, expected_return_pct=-0.15, catalyst_description="중국 조강 생산 감축 및 글로벌 원자재 조정")
            ),
            moat_description="호주 필바라 철광석과 칠레 구리 광산을 최저 원가로 채굴하는 글로벌 천연자원 절대 요새.",
            bottleneck_role="글로벌 인프라 및 전동화(구리)의 단일 최대 물리적 원자재 공급 통행세.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_bhp, iv_bhp),
            thesis_invalidation_triggers=["호주/칠레 정부의 광물 채굴세 50% 인상", "상온 초전도체 조기 상용화"]
        ))

        # 2. Cameco Corporation (CCJ / NYSE: CCJ) - Tier: SATELLITE (Nuclear Fuel Sovereign Bottleneck)
        p_ccj = self.price_service.get_price("MACRO-CCJ", 97.74)
        iv_ccj = p_ccj * 1.30
        cameco_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.6, inelasticity_score=9.8, buyer_quality_score=9.7, walled_garden_score=9.7, spillover_score=9.6
        )
        assets.append(Asset(
            id="MACRO-CCJ",
            name="Cameco Corporation (NYSE: CCJ / TSX: CCO)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_ccj,
            intrinsic_value_base=iv_ccj,
            tier=AssetTier.SATELLITE,
            skill_scores=cameco_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_ccj * 1.60, expected_return_pct=0.60, catalyst_description="서방의 러시아산 우라늄 전면 금수 및 SMR 원전 확산"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_ccj, expected_return_pct=0.30, catalyst_description="우라늄 장기계약 단가 $90+/lb 및 웨스팅하우스 시너지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_ccj * 0.82, expected_return_pct=-0.18, catalyst_description="카자흐스탄 공급 급증 및 우라늄 스팟 가격 조정")
            ),
            moat_description="캐나다 서스캐처원의 세계 최고 품위 우라늄 광산과 웨스팅하우스 지분을 보유한 서방 원전의 심장.",
            bottleneck_role="24/7 무탄소 기저 전력(원자력)의 대체 불가능한 단일 핵연료 공급 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_ccj, iv_ccj),
            thesis_invalidation_triggers=["대형 원전 사고 발생으로 글로벌 원자력 정책 중단"]
        ))

        # 3. Freeport-McMoRan (FCX / NYSE: FCX) - Tier: SATELLITE (Copper Electrification Kingpin)
        p_fcx = self.price_service.get_price("MACRO-FCX", 66.49)
        iv_fcx = p_fcx * 1.30
        fcx_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.3, inelasticity_score=9.6, buyer_quality_score=9.5, walled_garden_score=9.3, spillover_score=9.7
        )
        assets.append(Asset(
            id="MACRO-FCX",
            name="Freeport-McMoRan Inc. (NYSE: FCX)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_fcx,
            intrinsic_value_base=iv_fcx,
            tier=AssetTier.SATELLITE,
            skill_scores=fcx_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_fcx * 1.60, expected_return_pct=0.60, catalyst_description="AI 데이터센터 전력망 구리 수요 폭증으로 구리가격 $6.50/lb 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_fcx, expected_return_pct=0.30, catalyst_description="그라스버그 지하광산 순현금 창출 및 배당 확대"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_fcx * 0.81, expected_return_pct=-0.19, catalyst_description="글로벌 경기 둔화로 인한 구리 수요 일시적 둔화")
            ),
            moat_description="세계 최대 구리 광산 그라스버그를 보유하고 최저 원가로 구리를 생산하는 전력화 킹핀.",
            bottleneck_role="글로벌 AI 데이터센터 전력망 및 전동화의 필수 전도체 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_fcx, iv_fcx),
            thesis_invalidation_triggers=["인도네시아 정부의 광산 지분 강제 몰수"]
        ))

        # 4. Cheniere Energy (LNG / NYSE: LNG) - Tier: CORE (Atlantic LNG Export Monopoly)
        p_lng = self.price_service.get_price("MACRO-LNG", 271.64)
        iv_lng = p_lng * 1.25
        lng_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.4, inelasticity_score=9.3, buyer_quality_score=9.6, walled_garden_score=9.6, spillover_score=9.4
        )
        assets.append(Asset(
            id="MACRO-LNG",
            name="Cheniere Energy, Inc. (NYSE: LNG)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_lng,
            intrinsic_value_base=iv_lng,
            tier=AssetTier.CORE,
            skill_scores=lng_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_lng * 1.48, expected_return_pct=0.48, catalyst_description="사빈패스/코퍼스크리스티 증설 및 유럽/아시아 20년 고정 수수료 독점"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_lng, expected_return_pct=0.25, catalyst_description="Take-or-Pay 수수료 기반 안정적 FCF 창출 및 자사주 10% 소각"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_lng * 0.85, expected_return_pct=-0.15, catalyst_description="미국 에너지부의 LNG 수출 승인 동결")
            ),
            moat_description="미국 최대 LNG 액화 터미널을 운영하며 20년 고정 수수료를 징수하는 독점적 통행세 모델.",
            bottleneck_role="유럽 및 아시아의 에너지 안보를 책임지는 대서양 LNG 수출 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_lng, iv_lng),
            thesis_invalidation_triggers=["미국 정부의 LNG 수출 전면 금지 조치"]
        ))

        # 5. Physical Allocated Gold (XAU) - Tier: CORE
        p_gold = self.price_service.get_price("CMD-GOLD", 4458.50)
        iv_gold = p_gold * 1.25
        gold_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=10.0, inelasticity_score=9.9, buyer_quality_score=9.8, walled_garden_score=9.7, spillover_score=9.5
        )
        assets.append(Asset(
            id="CMD-GOLD",
            name="Physical Allocated Gold (XAU / Vault Reserve)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_gold,
            intrinsic_value_base=iv_gold,
            tier=AssetTier.CORE,
            skill_scores=gold_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_gold * 1.45, expected_return_pct=0.45, catalyst_description="글로벌 탈달러화 및 각국 중앙은행의 연 1,500톤 이상 금 매입 지속"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_gold, expected_return_pct=0.25, catalyst_description="글로벌 통화 공급량(M2) 팽창에 따른 연 8-10% 화폐가치 방어 복리 성장"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_gold * 0.90, expected_return_pct=-0.10, catalyst_description="미국 연준의 초긴축 복귀 및 실질 금리 급등")
            ),
            moat_description="5,000년간 입증된 인류 최후의 무위험 절대 화폐이자 디폴트 리스크 0%인 영구적 닻.",
            bottleneck_role="글로벌 부채 시스템 희석에 대항하는 궁극의 실물 담보.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_gold, iv_gold),
            thesis_invalidation_triggers=["전 세계 정부의 금 거래 및 소유 전면 몰수"]
        ))

        # 6. MP Materials (NYSE: MP) - Tier: SATELLITE (US Mountain Pass Rare Earths Monopoly)
        p_mp = self.price_service.get_price("MACRO-MP", 17.50)
        iv_mp = p_mp * 1.35
        mp_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.3, inelasticity_score=9.7, buyer_quality_score=9.6, walled_garden_score=9.5, spillover_score=9.6
        )
        assets.append(Asset(
            id="MACRO-MP",
            name="MP Materials Corp. (NYSE: MP)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_mp,
            intrinsic_value_base=iv_mp,
            tier=AssetTier.SATELLITE,
            skill_scores=mp_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_mp * 1.75, expected_return_pct=0.75, catalyst_description="중국의 희토류 자원 무기화 통제 강화 및 미 국방부/애플 영구자석 공급 독점"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_mp, expected_return_pct=0.35, catalyst_description="텍사스 포트워스 영구자석 제조 팹 가동으로 완전한 서방 희토류 내재화 달성"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_mp * 0.78, expected_return_pct=-0.22, catalyst_description="중국 희토류 채굴 쿼터 확대로 인한 가격 덤핑")
            ),
            moat_description="서방권 유일의 대규모 희토류(NdPr 네오디뮴) 채굴·정제 광산인 마운틴패스를 독점한 전략 안보 자산.",
            bottleneck_role="EV 모터, 풍력 터빈, F-35 스텔스기 영구자석의 필수 희토류 공급 킹핀.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_mp, iv_mp),
            thesis_invalidation_triggers=["희토류를 사용하지 않는 고효율 모터 상용화"]
        ))

        # 7. Nutrien (NYSE: NTR) - Tier: CORE (Global Agricultural Fertilizer & Potash Monopoly)
        p_ntr = self.price_service.get_price("MACRO-NTR", 48.50)
        iv_ntr = p_ntr * 1.28
        ntr_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.5, inelasticity_score=9.4, buyer_quality_score=9.5, walled_garden_score=9.4, spillover_score=9.2
        )
        assets.append(Asset(
            id="MACRO-NTR",
            name="Nutrien Ltd. (NYSE: NTR / TSX: NTR)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_ntr,
            intrinsic_value_base=iv_ntr,
            tier=AssetTier.CORE,
            skill_scores=ntr_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_ntr * 1.55, expected_return_pct=0.55, catalyst_description="러시아/벨라루스 칼륨 수출 제재 장기화 및 글로벌 곡물 수확량 감소로 비료가 급등"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_ntr, expected_return_pct=0.28, catalyst_description="캐나다 서스캐처원 칼륨 광산 최저원가 경쟁력 및 북미 2,000개 농업 소매망 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_ntr * 0.84, expected_return_pct=-0.16, catalyst_description="곡물 가격 하락으로 농가 비료 투입량 축소")
            ),
            moat_description="세계 최대 칼륨(Potash) 및 질소 비료 생산기업으로 인류 식량 생산의 대체 불가능한 화학적 비료 기둥.",
            bottleneck_role="80억 인류의 필수 식량 안보 및 농업 생산성 유지 필수 비료 독점 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_ntr, iv_ntr),
            thesis_invalidation_triggers=["생물학적 질소 고정 기술의 급격한 발전으로 화학 비료 대체"]
        ))

        # 8. Valero Energy (NYSE: VLO) - Tier: CORE (Refining Complexity & Export Cash Machine)
        p_vlo = self.price_service.get_price("MACRO-VLO", 145.00)
        iv_vlo = p_vlo * 1.25
        vlo_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.3, inelasticity_score=9.3, buyer_quality_score=9.4, walled_garden_score=9.5, spillover_score=9.0
        )
        assets.append(Asset(
            id="MACRO-VLO",
            name="Valero Energy Corporation (NYSE: VLO)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_vlo,
            intrinsic_value_base=iv_vlo,
            tier=AssetTier.CORE,
            skill_scores=vlo_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_vlo * 1.48, expected_return_pct=0.48, catalyst_description="글로벌 정제소 폐쇄에 따른 정제마진(Crack Spread) 슈퍼사이클 + 디젤/항공유 수출 급증"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_vlo, expected_return_pct=0.25, catalyst_description="멕시코만 초고도화 정제설비 최저비용 운영 및 연 10% 주주환원(자사주 소각/배당)"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_vlo * 0.85, expected_return_pct=-0.15, catalyst_description="글로벌 경기 침체로 수송용 연료 소비 급감")
            ),
            moat_description="미국 멕시코만의 세계 최고 고도화 정제 설비(Nelson Complexity 12+)를 통해 저품질 원유를 고마진 연료로 정제하는 현금 기계.",
            bottleneck_role="글로벌 정제 능력 부족 시대에 디젤, 가솔린, 항공유를 공급하는 대서양 정제 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_vlo, iv_vlo),
            thesis_invalidation_triggers=["전기차 100% 보급으로 수송용 연료 수요 소멸"]
        ))

        # 9. NextEra Energy (NYSE: NEE) - Tier: CORE (US Renewable & Grid Utility Fortress)
        p_nee = self.price_service.get_price("MACRO-NEE", 76.50)
        iv_nee = p_nee * 1.25
        nee_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.4, inelasticity_score=9.2, buyer_quality_score=9.6, walled_garden_score=9.6, spillover_score=9.4
        )
        assets.append(Asset(
            id="MACRO-NEE",
            name="NextEra Energy, Inc. (NYSE: NEE)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_nee,
            intrinsic_value_base=iv_nee,
            tier=AssetTier.CORE,
            skill_scores=nee_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_nee * 1.45, expected_return_pct=0.45, catalyst_description="빅테크 AI 데이터센터와의 대규모 태양광/ESS PPA 체결 및 플로리다 인구 유입 지속"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_nee, expected_return_pct=0.25, catalyst_description="연 6-8% 규제자산 기반 이익 성장 및 배당 복리 10% 인상"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_nee * 0.86, expected_return_pct=-0.14, catalyst_description="고금리 장기화로 인한 인프라 조달 비용 상승")
            ),
            moat_description="플로리다 최대 규제 전력 유틸리티(FPL)와 세계 최대 풍력/태양광 디벨로퍼를 겸비한 북미 전력 인프라 절대 강자.",
            bottleneck_role="북미 전력망 그리드 연결 및 친환경 AI 전력 공급의 핵심 유틸리티.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_nee, iv_nee),
            thesis_invalidation_triggers=["플로리다 공공서비스위원회의 요금 기저(Rate Base) 대규모 삭감"]
        ))

        # 10. Pan American Silver (NYSE: PAAS) - Tier: SATELLITE (Silver Industrial & Monetary Asymmetry)
        p_paas = self.price_service.get_price("MACRO-PAAS", 23.50)
        iv_paas = p_paas * 1.35
        paas_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.1, inelasticity_score=9.5, buyer_quality_score=9.3, walled_garden_score=9.2, spillover_score=9.7
        )
        assets.append(Asset(
            id="MACRO-PAAS",
            name="Pan American Silver Corp. (NYSE: PAAS / TSX: PAAS)",
            asset_class=AssetClass.COMMODITIES,
            current_price=p_paas,
            intrinsic_value_base=iv_paas,
            tier=AssetTier.SATELLITE,
            skill_scores=paas_scores,
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_paas * 1.70, expected_return_pct=0.70, catalyst_description="태양광 패널 및 AI 반도체 실버 페이스트 산업 수요 폭증으로 은 가격 $45/oz 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_paas, expected_return_pct=0.35, catalyst_description="야마나 골드 자산 통합 완료 및 남미 핵심 은 광산 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_paas * 0.78, expected_return_pct=-0.22, catalyst_description="남미 광산 국유화 규제 리스크 및 은 가격 단기 급락")
            ),
            moat_description="미주 대륙의 최상급 은 광산을 보유한 세계 최대 은 채굴 기업으로 산업용 전도체와 통화적 금속의 이중 수혜.",
            bottleneck_role="태양광 PV 셀, 반도체 및 전자 회로의 대체 불가능한 최고 효율 전기전도체(은) 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_paas, iv_paas),
            thesis_invalidation_triggers=["구리 또는 그래핀이 은의 전기전도성을 완전 대체"]
        ))

        return assets

    def get_global_macro_framework_summary(self) -> Dict[str, Any]:
        return {
            "macro_regime": "M2 Expansion & Physical Scarcity Paradigm",
            "critical_bottlenecks": [
                "1. AI Power & Grid Bottleneck (Uranium, Copper, High-Voltage Transformers)",
                "2. Sovereign Energy Security (LNG Export Terminals & Refining Complexity)",
                "3. Strategic Critical Materials (Rare Earths, Potash, Silver, Lithium)",
                "4. Monetary Debasement Hedge (Gold & Non-sovereign Hard Reserves)"
            ],
            "structural_tailwinds": "Physical supply-side inelasticity dominating over financial asset paper claims."
        }
