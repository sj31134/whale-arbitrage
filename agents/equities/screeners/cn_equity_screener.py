"""
Chinese Equity Screener: Institutional research and valuation for Chinese Equities
Expanded with tech & consumer champions (Kweichow Moutai, Tencent, NetEase, Meituan, Xiaomi, BYD, CATL, TIGER China Semi ETF).
"""
from typing import List
from src.core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from src.core.valuation import ValuationEngine
from src.core.scoring_engine import ScoringEngine
from src.data_pipeline.live_price_service import LivePriceService


class CNEquityScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_cn_equity_universe(self) -> List[Asset]:
        return self.get_screened_universe()

    def get_screened_universe(self) -> List[Asset]:
        assets: List[Asset] = []

        # 1. Kweichow Moutai (600519.SH) - Tier: CORE
        p_moutai = self.price_service.get_price("CN-600519", 1341.99)
        iv_moutai = p_moutai * 1.30
        assets.append(Asset(
            id="CN-600519", name="Kweichow Moutai Co., Ltd. (600519.SH)", asset_class=AssetClass.EQUITIES,
            current_price=p_moutai, intrinsic_value_base=iv_moutai, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.9, 9.8, 9.9, 9.9, 9.2),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_moutai * 1.58, expected_return_pct=0.58, catalyst_description="중국 내수 경기 부양책 본격화 + 출고가 20% 인상 + 특별 배당 확대"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_moutai, expected_return_pct=0.30, catalyst_description="영업이익률 65%+ 및 수조 원 무이자 선수금 기반 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_moutai * 0.83, expected_return_pct=-0.17, catalyst_description="중국 고급 소비재 둔화 장기화")
            ),
            moat_description="적수하 유역의 미생물 자연 독점과 1,000년 전통의 문화적 지대로 인해 100% 무이자 선수금을 받는 중국 최고의 가치저장 소비재.",
            bottleneck_role="중국 비즈니스 접대와 정·재계 최상위층 네트워킹의 대체 불가능한 단일 기축통화.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_moutai, iv_moutai),
            thesis_invalidation_triggers=["마오타이주 맛과 향을 100% 복제하는 화학적 대체재 등장"]
        ))

        # 2. Tencent Holdings (0700.HK) - Tier: CORE
        p_tencent = self.price_service.get_price("CN-0700", 440.00)
        iv_tencent = p_tencent * 1.28
        assets.append(Asset(
            id="CN-0700", name="Tencent Holdings Limited (0700.HK)", asset_class=AssetClass.EQUITIES,
            current_price=p_tencent, intrinsic_value_base=iv_tencent, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.7, 9.9, 9.8, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_tencent * 1.55, expected_return_pct=0.55, catalyst_description="위챗 미니프로그램 전자상거래 GMV 급증 + 연 100억 달러 자사주 소각"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_tencent, expected_return_pct=0.28, catalyst_description="13억 위챗 DAU 기반 게임/광고/핀테크 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_tencent * 0.84, expected_return_pct=-0.16, catalyst_description="중국 정부의 게임 규제 재강화")
            ),
            moat_description="13억 중국인이 매일 사용하는 위챗(WeChat) 메신저, 결제, 미니앱을 독점한 중국 디지털 일상의 단일 플랫폼.",
            bottleneck_role="중국 인터넷 트래픽과 모바일 금융 결제의 관문 통행세.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_tencent, iv_tencent),
            thesis_invalidation_triggers=["위챗을 대체하는 새로운 차세대 소셜 플랫폼의 부상"]
        ))

        # 3. NetEase (9999.HK) - Tier: CORE (Global Gaming IP & Pure FCF Machine)
        p_netease = self.price_service.get_price("CN-9999", 145.00)
        iv_netease = p_netease * 1.30
        assets.append(Asset(
            id="CN-9999", name="NetEase, Inc. (9999.HK / NASDAQ: NTES)", asset_class=AssetClass.EQUITIES,
            current_price=p_netease, intrinsic_value_base=iv_netease, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.6, 9.7, 9.7, 9.3),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_netease * 1.58, expected_return_pct=0.58, catalyst_description="블리자드(와우/하스스톤) 재계약 풀서비스 가동 + '어디에도 없는 나라(Where Winds Meet)' 글로벌 히트"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_netease, expected_return_pct=0.30, catalyst_description="150억 달러 순현금 요새 및 분기 배당성향 30%+ 지속"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_netease * 0.82, expected_return_pct=-0.18, catalyst_description="신작 게임 판호(허가) 발급 지연")
            ),
            moat_description="자체 개발 고마진 게임 IP(몽환서유 등)와 150억 달러의 무차입 순현금을 보유한 고배당 FCF 머신.",
            bottleneck_role="중국 및 아시아 하드코어 게이머의 시간과 돈을 점유하는 디지털 엔터테인먼트 요새.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_netease, iv_netease),
            thesis_invalidation_triggers=["핵심 게임 IP 매출이 3년 연속 50% 이상 급감할 때"]
        ))

        # 4. Meituan (3690.HK) - Tier: SATELLITE (China Local Services & Delivery 70% Monopoly)
        p_meituan = self.price_service.get_price("CN-3690", 168.00)
        iv_meituan = p_meituan * 1.30
        assets.append(Asset(
            id="CN-3690", name="Meituan (3690.HK)", asset_class=AssetClass.EQUITIES,
            current_price=p_meituan, intrinsic_value_base=iv_meituan, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.5, 9.4, 9.6, 9.7, 9.5),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_meituan * 1.62, expected_return_pct=0.62, catalyst_description="음식배달 OPM 20% 도달 + 해외 진출(KeeTa 중동/남미) 성공 + 드론 배송 상용화"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_meituan, expected_return_pct=0.30, catalyst_description="중국 로컬 라이프스타일 70% 점유율 수성 및 자사주 10억 달러 소각"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_meituan * 0.81, expected_return_pct=-0.19, catalyst_description="틱톡(도우인)과의 로컬 배달 출혈 경쟁 재점화")
            ),
            moat_description="수백만 명의 라이더 네트워크와 7억 명의 사용자를 묶어 중국 음식 배달과 호텔/매장 결제를 독점한 로컬 플랫폼.",
            bottleneck_role="중국 14억 인구의 일상 식생활 및 온-오프라인 물리적 최종 라스트마일 배송 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_meituan, iv_meituan),
            thesis_invalidation_triggers=["도우인이 음식 배달 시장 점유율 50%를 탈환할 때"]
        ))

        # 5. Xiaomi (1810.HK) - Tier: SATELLITE (Smartphone, IoT & SU7 EV Ecosystem)
        p_xiaomi = self.price_service.get_price("CN-1810", 28.50)
        iv_xiaomi = p_xiaomi * 1.35
        assets.append(Asset(
            id="CN-1810", name="Xiaomi Corporation (1810.HK)", asset_class=AssetClass.EQUITIES,
            current_price=p_xiaomi, intrinsic_value_base=iv_xiaomi, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.4, 9.3, 9.5, 9.6, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_xiaomi * 1.70, expected_return_pct=0.70, catalyst_description="SU7/Ultra 전기차 연 20만 대 인도 돌파 + HyperOS 스마트폰/IoT/자동차 생태계 락인"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_xiaomi, expected_return_pct=0.35, catalyst_description="글로벌 스마트폰 점유율 3위 유지 및 인터넷 서비스 고마진 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_xiaomi * 0.78, expected_return_pct=-0.22, catalyst_description="전기차 가격 경쟁 격화로 인한 자동차 사업부 적자 확대")
            ),
            moat_description="스마트폰, 스마트 가전 IoT, 그리고 성공적으로 안착한 SU7 전기차를 단일 운영체제(HyperOS)로 결합한 차세대 하드웨어 생태계.",
            bottleneck_role="글로벌 스마트 디바이스와 커넥티드 카의 가성비 및 초연결 생태계 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_xiaomi, iv_xiaomi),
            thesis_invalidation_triggers=["스마트폰 사업부의 글로벌 출하량이 급감하여 생태계 붕괴"]
        ))

        # 6. TIGER ETF (396520.KS)
        p_tiger_cn = self.price_service.get_price("CN-ETF-396520", 14540.0)
        assets.append(Asset(
            id="CN-ETF-396520", name="TIGER China Semiconductor FACTSET ETF (396520.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_tiger_cn, intrinsic_value_base=p_tiger_cn * 1.30, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.5, 9.6, 9.5, 9.6, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_tiger_cn * 1.60, expected_return_pct=0.60, catalyst_description="중국 국가반도체 대기금 3기(3,440억 위안) 전액 집행 및 반도체 국산화율 50% 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_tiger_cn * 1.30, expected_return_pct=0.30, catalyst_description="SMIC, 나우라(NAURA), 파이오텍 등 중국 반도체 자립 바스켓 실적 견조"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_tiger_cn * 0.80, expected_return_pct=-0.20, catalyst_description="미국의 대중국 반도체 장비 및 EDA 소프트웨어 전면 차단")
            ),
            moat_description="중국 정부의 60조 원 규모 국가 반도체 펀드 수혜를 받는 1등 국산화 장비/팹 바스켓.",
            bottleneck_role="중국 반도체 국산화 자립화의 필수 바스켓.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_tiger_cn, p_tiger_cn * 1.30),
            thesis_invalidation_triggers=["중국 반도체 자립화 프로젝트의 전면 중단"]
        ))

        return assets
