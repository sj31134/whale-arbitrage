"""
Korean Equity Screener: Institutional research and valuation for Korean Equities
Expanded with global champions (현대차, 기아, 알테오젠, 에이피알, 리가켐바이오, 두산에너빌리티, 삼성전자, SK하이닉스, HD현대일렉트릭, 메리츠금융지주, 삼바, 한화에어로).
"""
from typing import List
from ..core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from ..core.valuation import ValuationEngine
from ..core.scoring_engine import ScoringEngine
from ..data_pipeline.live_price_service import LivePriceService


class KREquityScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_kr_equity_universe(self) -> List[Asset]:
        return self.get_screened_universe()

    def get_screened_universe(self) -> List[Asset]:
        assets: List[Asset] = []

        # 1. Samsung Electronics (005930.KS)
        p_samsung = self.price_service.get_price("KR-005930", 274500.0)
        iv_samsung = p_samsung * 1.26
        assets.append(Asset(
            id="KR-005930", name="Samsung Electronics (005930.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_samsung, intrinsic_value_base=iv_samsung, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.5, 9.6, 9.6, 9.4),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_samsung * 1.52, expected_return_pct=0.52, catalyst_description="HBM4 커스텀 베이스다이 공급 + 평택 팹 DDR5/eSSD 서버 메모리 마진 50% 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_samsung, expected_return_pct=0.26, catalyst_description="100조 원 순현금 기반 배당 및 범용 D램/낸드 슈퍼사이클 정상화"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_samsung * 0.85, expected_return_pct=-0.15, catalyst_description="파운드리 적자 지속 및 HBM 공급사 내 점유율 경쟁 심화")
            ),
            moat_description="100조 원 이상의 무차입 순현금과 평택/기흥 반도체 팹 인프라를 보유한 글로벌 1위 메모리 요새.",
            bottleneck_role="글로벌 AI 데이터센터와 스마트폰/PC의 필수 디지털 기억소자 공급 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_samsung, iv_samsung),
            thesis_invalidation_triggers=["중국 창신메모리(CXMT)가 첨단 DDR5 수율 80%를 달성하여 덤핑할 때"]
        ))

        # 2. Meritz Financial Group (138040.KS) - Tier: CORE
        p_meritz = self.price_service.get_price("KR-138040", 116700.0)
        iv_meritz = p_meritz * 1.30
        assets.append(Asset(
            id="KR-138040", name="Meritz Financial Group (138040.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_meritz, intrinsic_value_base=iv_meritz, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.7, 9.8, 9.8, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_meritz * 1.62, expected_return_pct=0.62, catalyst_description="연 1.5조 원 자사주 매입/소각 집행으로 유통주식수 7% 감소 + 밸류업 지수 1위 편입"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_meritz, expected_return_pct=0.30, catalyst_description="당기순이익 50% 주주환원 원칙 철저 준수 및 ROE 25%+ 유지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_meritz * 0.84, expected_return_pct=-0.16, catalyst_description="부동산 PF 부실 발생으로 대손충당금 급증")
            ),
            moat_description="한국 최고 수준의 자본배치 원칙과 보험 무이자 플로트를 활용하여 순이익의 50%를 전액 자사주 매입/소각하는 한국판 버크셔 해서웨이.",
            bottleneck_role="자본시장 밸류업 정책의 대체 불가능한 단일 지배구조 롤모델.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_meritz, iv_meritz),
            thesis_invalidation_triggers=["주주환원율 50% 약속 철회 또는 비핵심 사업부 지배권 인수"]
        ))

        # 3. Hyundai Motor (005380.KS) - Tier: CORE (India IPO Cash Fortress & Hybrid/Robotics Giant)
        p_hmc = self.price_service.get_price("KR-005380", 285000.0)
        iv_hmc = p_hmc * 1.30
        assets.append(Asset(
            id="KR-005380", name="Hyundai Motor Company (005380.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_hmc, intrinsic_value_base=iv_hmc, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.4, 9.6, 9.7, 9.5),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_hmc * 1.58, expected_return_pct=0.58, catalyst_description="인도법인 IPO 성공으로 4조 원 현금 유입 + 3개년 4조 원 자사주 매입소각 + 보스턴다이내믹스 로보틱스 가치 부각"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_hmc, expected_return_pct=0.30, catalyst_description="하이브리드(HEV) 판매 비중 15% 돌파 및 글로벌 OPM 9.5%+ 견조한 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_hmc * 0.83, expected_return_pct=-0.17, catalyst_description="미국 관세 리스크 발생 및 인센티브 급증")
            ),
            moat_description="글로벌 Top 3 완성차 기업으로 인도 자동차 시장 2위 독점, 하이브리드 엔진 기술력, 보스턴다이내믹스 로봇 제어 기술을 결합한 밸류업 대장주.",
            bottleneck_role="글로벌 모빌리티 전동화 전환기의 유연한 하이브리드 파워트레인 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_hmc, iv_hmc),
            thesis_invalidation_triggers=["북미 시장 전기차 보조금 전면 중단 및 점유율 급락"]
        ))

        # 4. Alteogen (196170.KQ) - Tier: SATELLITE (Global SC Hyaluronidase Platform Monopoly)
        p_alt = self.price_service.get_price("KR-196170", 385000.0)
        iv_alt = p_alt * 1.35
        assets.append(Asset(
            id="KR-196170", name="Alteogen Inc. (196170.KQ)", asset_class=AssetClass.EQUITIES,
            current_price=p_alt, intrinsic_value_base=iv_alt, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.9, 9.9, 9.9, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_alt * 1.75, expected_return_pct=0.75, catalyst_description="머크(MSD) 키트루다 SC 상용화로 연 1조 원 로열티 유입 + 추가 빅파마 3곳 기술이전"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_alt, expected_return_pct=0.35, catalyst_description="인간 히알루로니다제 ALT-B4 글로벌 독점 지위 및 품목허가 마일스톤 유입"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_alt * 0.76, expected_return_pct=-0.24, catalyst_description="FDA 허가 지연 및 할로자임과의 특허 소송 리스크")
            ),
            moat_description="정맥주사(IV)를 5분 피하주사(SC)로 바꾸는 인간 히알루로니다제 재조합 기술을 보유하여 전 세계 빅파마 항암제 특허를 2040년까지 연장해 주는 독점 플랫폼.",
            bottleneck_role="글로벌 블록버스터 바이오의약품(키트루다 등)의 피하주사 제형 전환 필수 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_alt, iv_alt),
            thesis_invalidation_triggers=["키트루다 SC 제형 임상 3상 최종 품목허가 반려"]
        ))

        # 5. HD Hyundai Electric (267260.KS) - Tier: SATELLITE
        p_hd_elec = self.price_service.get_price("KR-267260", 803000.0)
        assets.append(Asset(
            id="KR-267260", name="HD Hyundai Electric (267260.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_hd_elec, intrinsic_value_base=p_hd_elec * 1.30, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.9, 9.7, 9.8, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_hd_elec * 1.62, expected_return_pct=0.62, catalyst_description="북미 빅테크 AI 데이터센터 전용 변압기 5년 치 공급 독점 + OPM 30% 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_hd_elec * 1.30, expected_return_pct=0.30, catalyst_description="울산/앨라배마 증설 공장 가동 및 2029년까지 완판된 5조 원 수주잔고 실적 반영"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_hd_elec * 0.81, expected_return_pct=-0.19, catalyst_description="원자재(구리/방향성 규소강판) 가격 급등으로 마진 훼손")
            ),
            moat_description="초고압 변압기(500kV+) 제작 기술과 북미 앨라배마 팹을 선점하여 2029년까지 도크가 마감된 전력망 슈퍼사이클의 심장.",
            bottleneck_role="북미 전력망 교체 및 AI 데이터센터 전력 수전의 단일 물리적 공급 병목.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_hd_elec, p_hd_elec * 1.30),
            thesis_invalidation_triggers=["중국산 초고압 변압기의 미국 전력망 진입 규제 전면 해제"]
        ))

        # 6. APR (278470.KS) - Tier: SATELLITE (Global K-Beauty Meditech Champion)
        p_apr = self.price_service.get_price("KR-278470", 265000.0)
        iv_apr = p_apr * 1.35
        assets.append(Asset(
            id="KR-278470", name="APR Co., Ltd. (278470.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_apr, intrinsic_value_base=iv_apr, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.3, 9.5, 9.4, 9.6, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_apr * 1.70, expected_return_pct=0.70, catalyst_description="미국 아마존/틱톡샵 뷰티 디바이스 1위 독점 + 평택 제2공장 가동으로 글로벌 수출 70% 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_apr, expected_return_pct=0.35, catalyst_description="메디큐브 부스터 프로 및 화장품 고마진 번들 판매로 OPM 25%+ 지속"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_apr * 0.78, expected_return_pct=-0.22, catalyst_description="중국 저가 모방 제품 유입으로 마케팅 비용 증가")
            ),
            moat_description="자체 R&D와 평택 스마트 팩토리를 통해 홈 뷰티 디바이스와 기능성 화장품을 전 세계 D2C로 직판하는 글로벌 K-메디테크 요새.",
            bottleneck_role="글로벌 홈 뷰티 케어 시장의 디지털 미용기기 독점 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_apr, iv_apr),
            thesis_invalidation_triggers=["글로벌 대형 뷰티 그룹(로레알 등)의 독점 모방 기기 출시"]
        ))

        # 7. Doosan Enerbility (034020.KS) - Tier: SATELLITE (SMR & Gas Turbine Foundry)
        p_doosan = self.price_service.get_price("KR-034020", 21500.0)
        iv_doosan = p_doosan * 1.30
        assets.append(Asset(
            id="KR-034020", name="Doosan Enerbility Co., Ltd. (034020.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_doosan, intrinsic_value_base=iv_doosan, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.4, 9.6, 9.5, 9.5, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_doosan * 1.65, expected_return_pct=0.65, catalyst_description="체코/폴란드 대형 원전 본계약 체결 + 뉴스케일/엑스에너지 SMR 단조 주기기 양산 독점"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_doosan, expected_return_pct=0.30, catalyst_description="한국형 대형 가스터빈 공급 확대 및 원전 주기기 수주잔고 15조 원 돌파"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_doosan * 0.81, expected_return_pct=-0.19, catalyst_description="해외 원전 수주 웨스팅하우스 지재권 분쟁 장기화")
            ),
            moat_description="17,000톤 단조 프레스와 원자로 격납용기/터빈을 일괄 생산할 수 있는 전 세계 극소수의 원자력 파운드리.",
            bottleneck_role="서방 대형 원전 및 차세대 SMR 주기기 물리적 제조의 독점 위탁제조 병목.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_doosan, iv_doosan),
            thesis_invalidation_triggers=["국내 및 글로벌 탈원전 정책 회귀"]
        ))

        # 8. SK hynix (000660.KS), Samsung Biologics (207940.KS), Hanwha Aerospace (012450.KS)
        p_skh = self.price_service.get_price("KR-000660", 1645000.0)
        assets.append(Asset(
            id="KR-000660", name="SK hynix (000660.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_skh, intrinsic_value_base=p_skh * 1.28, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.7, 9.8, 9.8, 9.7, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_skh * 1.58, expected_return_pct=0.58, catalyst_description="MR-MUF 공정 12단/16단 HBM3E 및 HBM4 엔비디아 독점 공급 지속"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_skh * 1.28, expected_return_pct=0.28, catalyst_description="HBM 점유율 50%+ 및 D램 영업이익률 40%+ 유지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_skh * 0.82, expected_return_pct=-0.18, catalyst_description="삼성전자 및 마이크론의 HBM3E 공급 진입으로 ASP 하락")
            ),
            moat_description="MR-MUF 첨단 패키징 공정을 기반으로 엔비디아 AI 가속기에 HBM을 선점 공급하는 글로벌 메모리 챔피언.",
            bottleneck_role="초고대역폭 메모리(HBM)의 최고 수율 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_skh, p_skh * 1.28),
            thesis_invalidation_triggers=["차세대 HBM 표준에서 기술적 주도권 상실"]
        ))

        p_sba = self.price_service.get_price("KR-207940", 1548000.0)
        assets.append(Asset(
            id="KR-207940", name="Samsung Biologics (207940.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_sba, intrinsic_value_base=p_sba * 1.28, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.7, 9.6, 9.8, 9.8, 9.5),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_sba * 1.52, expected_return_pct=0.52, catalyst_description="미국 생물보안법 통과에 따른 우시바이오 반사이익 + 5공장 조기 풀가동"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_sba * 1.28, expected_return_pct=0.28, catalyst_description="78.4만 리터 글로벌 1위 CDMO 생산능력 및 글로벌 Top 20 빅파마 락인"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_sba * 0.84, expected_return_pct=-0.16, catalyst_description="빅파마 파이프라인 임상 실패에 따른 수주 취소")
            ),
            moat_description="세계 최대 바이오의약품 위탁생산(CDMO) 캐파를 보유하고 압도적 공기 단축 기술을 독점한 바이오 파운드리.",
            bottleneck_role="글로벌 항체 의약품 생산의 대체 불가능한 단일 최대 제조 팹.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_sba, p_sba * 1.28),
            thesis_invalidation_triggers=["바이오의약품 cGMP 심사에서 대규모 경고장 수령"]
        ))

        return assets
