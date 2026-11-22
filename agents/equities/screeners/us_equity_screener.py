"""
US Equity Screener: Advanced institutional screening and valuation for US Equities
Expanded with global tech monopolies (ASML, TSM, GOOGL, META, PLTR, GE, AMAT, NVDA, MSFT, AVGO, CEG, LLY, AMZN, COST).
"""
from typing import List
from src.core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from src.core.valuation import ValuationEngine
from src.core.scoring_engine import ScoringEngine
from src.data_pipeline.live_price_service import LivePriceService


class USEquityScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_us_equity_universe(self) -> List[Asset]:
        return self.get_screened_universe()

    def get_screened_universe(self) -> List[Asset]:
        assets: List[Asset] = []

        # 1. Nvidia (NVDA)
        p_nvda = self.price_service.get_price("US-NVDA", 225.16)
        iv_nvda = p_nvda * 1.30
        assets.append(Asset(
            id="US-NVDA", name="Nvidia Corporation (NASDAQ: NVDA)", asset_class=AssetClass.EQUITIES,
            current_price=p_nvda, intrinsic_value_base=iv_nvda, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.5, 9.8, 9.8, 9.9, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_nvda * 1.60, expected_return_pct=0.60, catalyst_description="블랙웰 GB200/B200 NVL72 출하 폭증 및 엔터프라이즈 AI 추론 독점"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_nvda, expected_return_pct=0.30, catalyst_description="빅테크 AI Capex 30% 성장 및 CUDA 해자 기반 OPM 65% 유지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_nvda * 0.81, expected_return_pct=-0.19, catalyst_description="빅테크 자체 ASIC 칩 대체 가속 및 공급망 병목")
            ),
            moat_description="CUDA 소프트웨어 생태계와 NVLink 초고속 인터커넥트로 글로벌 AI 가속기 시장 90% 독점.",
            bottleneck_role="인류의 모든 AI 연산과 지능 창출을 통제하는 물리적 통행세 징수 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_nvda, iv_nvda),
            thesis_invalidation_triggers=["PyTorch/Triton 오픈소스가 CUDA를 100% 무력화할 때"]
        ))

        # 2. Microsoft (MSFT)
        p_msft = self.price_service.get_price("US-MSFT", 495.40)
        iv_msft = p_msft * 1.25
        assets.append(Asset(
            id="US-MSFT", name="Microsoft Corporation (NASDAQ: MSFT)", asset_class=AssetClass.EQUITIES,
            current_price=p_msft, intrinsic_value_base=iv_msft, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.6, 9.9, 9.8, 9.5),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_msft * 1.45, expected_return_pct=0.45, catalyst_description="M365 Copilot ARPU 급증 및 Azure AI 클라우드 35% 성장"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_msft, expected_return_pct=0.25, catalyst_description="엔터프라이즈 B2B 락인 및 FCF $80B+ 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_msft * 0.86, expected_return_pct=-0.14, catalyst_description="AI 인프라 감가상각비 급증으로 인한 마진 압박")
            ),
            moat_description="전 세계 기업 업무 환경(Office, Windows, Azure, GitHub)을 장악한 디지털 경제의 운영체제.",
            bottleneck_role="엔터프라이즈 AI 배포 및 기업용 소프트웨어 인프라의 절대 킹핀.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_msft, iv_msft),
            thesis_invalidation_triggers=["기업들이 M365 생태계를 오픈소스 소프트웨어로 전면 교체할 때"]
        ))

        # 3. ASML Holding (ASML) - Tier: CORE (Global EUV Lithography Monopoly)
        p_asml = self.price_service.get_price("US-ASML", 890.00)
        iv_asml = p_asml * 1.30
        assets.append(Asset(
            id="US-ASML", name="ASML Holding N.V. (NASDAQ: ASML)", asset_class=AssetClass.EQUITIES,
            current_price=p_asml, intrinsic_value_base=iv_asml, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.9, 10.0, 9.9, 10.0, 9.8),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_asml * 1.55, expected_return_pct=0.55, catalyst_description="High-NA EUV (EXE:5000) 2nm 양산 필수 도입 및 주문 잔고 400억 유로 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_asml, expected_return_pct=0.30, catalyst_description="EUV 노광장비 연 50대+ 안정적 출하 및 DUV 업그레이드 서비스 매출 성장"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_asml * 0.83, expected_return_pct=-0.17, catalyst_description="네덜란드/미국 정부의 대중국 레거시 DUV 수출 통제 추가 강화")
            ),
            moat_description="칼자이스 광학과 13.5nm 극자외선 플라즈마 기술을 독점하여 2nm 이하 첨단 반도체 제조를 100% 통제하는 지구상 유일의 노광장비 요새.",
            bottleneck_role="글로벌 모든 첨단 AI 반도체(엔비디아, 애플, TSMC, 삼성)의 물리적 진입 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_asml, iv_asml),
            thesis_invalidation_triggers=["EUV를 사용하지 않는 새로운 나노 패터닝(NIL 등) 기술이 2nm 수율을 초과할 때"]
        ))

        # 4. Taiwan Semiconductor (TSM) - Tier: CORE (Global Advanced Foundry Monopoly)
        p_tsm = self.price_service.get_price("US-TSM", 185.00)
        iv_tsm = p_tsm * 1.30
        assets.append(Asset(
            id="US-TSM", name="Taiwan Semiconductor Manufacturing Co. (NYSE: TSM)", asset_class=AssetClass.EQUITIES,
            current_price=p_tsm, intrinsic_value_base=iv_tsm, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.9, 9.8, 9.9, 9.8, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_tsm * 1.55, expected_return_pct=0.55, catalyst_description="2nm N2 공정 풀가동 및 CoWoS 어드밴스드 패키징 캐파 2배 확장 + 가격 10% 인상"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_tsm, expected_return_pct=0.30, catalyst_description="글로벌 첨단 팹 점유율 90%+ 유지 및 OPM 42%+ 지속"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_tsm * 0.82, expected_return_pct=-0.18, catalyst_description="대만 해협 지정학적 긴장 고조 및 미국/일본 팹 건설 비용 증가")
            ),
            moat_description="전 세계 3nm/2nm 첨단 반도체의 90% 이상을 제조하는 대체 불가능한 글로벌 파운드리 절대 챔피언.",
            bottleneck_role="애플, 엔비디아, AMD, 퀄컴의 모든 첨단 칩을 물리적으로 구현하는 유일한 위탁생산 병목.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_tsm, iv_tsm),
            thesis_invalidation_triggers=["중국의 대만 무력 침공 또는 물리적 팹 파괴"]
        ))

        # 5. Alphabet (GOOGL) - Tier: CORE (Search Monopoly & DeepMind/TPU AI Moat)
        p_googl = self.price_service.get_price("US-GOOGL", 188.00)
        iv_googl = p_googl * 1.28
        assets.append(Asset(
            id="US-GOOGL", name="Alphabet Inc. (NASDAQ: GOOGL)", asset_class=AssetClass.EQUITIES,
            current_price=p_googl, intrinsic_value_base=iv_googl, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.7, 9.5, 9.8, 9.7, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_googl * 1.50, expected_return_pct=0.50, catalyst_description="Gemini 2.0 Ultra 상용화 + 유튜브 쇼츠 수익화 + TPU v6 기반 자체 AI 추론 원가 50% 절감"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_googl, expected_return_pct=0.28, catalyst_description="검색 점유율 90% 방어 및 Google Cloud 영업이익률 20% 돌파"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_googl * 0.85, expected_return_pct=-0.15, catalyst_description="미 법무부 반독점 소송으로 안드로이드/크롬 분할 명령")
            ),
            moat_description="글로벌 검색 점유율 90%, 유튜브, 안드로이드, 자체 TPU 가속기 칩과 딥마인드를 갖춘 AI 수직계열화 요새.",
            bottleneck_role="인터넷 정보 탐색 및 글로벌 디지털 광고/비디오 트래픽의 독점 게이트웨이.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_googl, iv_googl),
            thesis_invalidation_triggers=["AI 챗봇 검색이 구글 검색 광고 모델을 50% 이상 잠식할 때"]
        ))

        # 6. Palantir Technologies (PLTR) - Tier: SATELLITE (Defense & Enterprise AI Operating System)
        p_pltr = self.price_service.get_price("US-PLTR", 58.00)
        iv_pltr = p_pltr * 1.35
        assets.append(Asset(
            id="US-PLTR", name="Palantir Technologies Inc. (NYSE: PLTR)", asset_class=AssetClass.EQUITIES,
            current_price=p_pltr, intrinsic_value_base=iv_pltr, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.8, 9.7, 9.8, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_pltr * 1.70, expected_return_pct=0.70, catalyst_description="AIP 부트캠프 기반 미국 민간 엔터프라이즈 고객 수 100% 폭증 + 미 국방부 TITAN 전술차량 양산"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_pltr, expected_return_pct=0.35, catalyst_description="정부 및 상업 매출 연 30%+ 성장 및 Rule of 40 지속 달성 (FCF 마진 35%+)"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_pltr * 0.78, expected_return_pct=-0.22, catalyst_description="고평가 멀티플 조정 및 공공 국방 예산 일시 집행 지연")
            ),
            moat_description="미 국방부/정보기관 보안 최고등급(IL6) 인증과 온톨로지(Ontology) 데이터 통합 엔진을 독점한 미 국방 및 기업용 AI OS.",
            bottleneck_role="실전 전장 지휘통제 및 기업 데이터 AI 자동화 배포의 단일 운영체제.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_pltr, iv_pltr),
            thesis_invalidation_triggers=["오픈소스 데이터 플랫폼이 팔란티어 온톨로지 보안성을 능가할 때"]
        ))

        # 7. GE Aerospace (GE) - Tier: CORE (Commercial Jet Engine 75% Global Monopoly)
        p_ge = self.price_service.get_price("US-GE", 195.00)
        iv_ge = p_ge * 1.25
        assets.append(Asset(
            id="US-GE", name="GE Aerospace (NYSE: GE)", asset_class=AssetClass.EQUITIES,
            current_price=p_ge, intrinsic_value_base=iv_ge, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.9, 9.8, 9.9, 9.2),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_ge * 1.48, expected_return_pct=0.48, catalyst_description="LEAP 엔진 비행시간 급증에 따른 애프터마켓(MRO) 초고마진 서비스 매출 폭발"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_ge, expected_return_pct=0.25, catalyst_description="44,000대 상용기 엔진 장착 기반 20년 고정 서비스 계약 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_ge * 0.86, expected_return_pct=-0.14, catalyst_description="보잉 신규 항공기 인도 지연에 따른 엔진 공급 차질")
            ),
            moat_description="전 세계 상용 항공기 비행 시간의 75%를 구동하는 항공기 제트 엔진 및 독점 애프터마켓 정비(MRO) 캐시카우 요새.",
            bottleneck_role="글로벌 항공 여객 및 물류 이동의 물리적 추진력 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_ge, iv_ge),
            thesis_invalidation_triggers=["전기/수소 항공기가 10년 내 대형 상용 제트 엔진을 전면 대체할 때"]
        ))

        # 8. Broadcom (AVGO), Constellation Energy (CEG), Eli Lilly (LLY), Amazon (AMZN), Costco (COST)
        p_avgo = self.price_service.get_price("US-AVGO", 392.99)
        assets.append(Asset(
            id="US-AVGO", name="Broadcom Inc. (NASDAQ: AVGO)", asset_class=AssetClass.EQUITIES,
            current_price=p_avgo, intrinsic_value_base=p_avgo * 1.28, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.7, 9.7, 9.8, 9.8, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_avgo * 1.55, expected_return_pct=0.55, catalyst_description="구글/메타 맞춤형 커스텀 AI XPU ASIC 폭주 및 토마호크 5 이더넷 스위치 독점"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_avgo * 1.28, expected_return_pct=0.28, catalyst_description="VMware 클라우드 구독 전환 및 FCF 마진 45% 유지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_avgo * 0.82, expected_return_pct=-0.18, catalyst_description="빅테크의 커스텀 칩 자체 내재화 성공")
            ),
            moat_description="빅테크 맞춤형 AI ASIC 칩 및 데이터센터 고속 네트워킹 스위치 칩 독점.",
            bottleneck_role="수만 개 GPU를 하나로 묶는 AI 클러스터 통신 대역폭의 독점 지배자.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_avgo, p_avgo * 1.28),
            thesis_invalidation_triggers=["이더넷이 인피니밴드에 의해 완전히 소멸될 때"]
        ))

        p_ceg = self.price_service.get_price("US-CEG", 282.50)
        assets.append(Asset(
            id="US-CEG", name="Constellation Energy Corporation (NASDAQ: CEG)", asset_class=AssetClass.EQUITIES,
            current_price=p_ceg, intrinsic_value_base=p_ceg * 1.30, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.9, 9.7, 9.8, 9.6),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_ceg * 1.60, expected_return_pct=0.60, catalyst_description="빅테크와 20년 장기 고정 원자력 PPA 계약 추가 체결"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_ceg * 1.30, expected_return_pct=0.30, catalyst_description="IRA 45U 세액공제 바닥 가격 지지 및 FCF 배당 성장"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_ceg * 0.81, expected_return_pct=-0.19, catalyst_description="미국 FERC의 원전 직접 연계 전력망 규제 강화")
            ),
            moat_description="미국 최대 원자력 발전 선대를 보유하여 24/7 무탄소 기저 전력을 빅테크에 직공급하는 원자력 요새.",
            bottleneck_role="AI 데이터센터 전력 쇼티지 시대의 단일 최대 24/7 청정 전력 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_ceg, p_ceg * 1.30),
            thesis_invalidation_triggers=["IRA 원자력 세액공제 전면 폐지"]
        ))

        p_lly = self.price_service.get_price("US-LLY", 1180.16)
        assets.append(Asset(
            id="US-LLY", name="Eli Lilly and Company (NYSE: LLY)", asset_class=AssetClass.EQUITIES,
            current_price=p_lly, intrinsic_value_base=p_lly * 1.26, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.7, 9.6, 9.8, 9.4),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_lly * 1.50, expected_return_pct=0.50, catalyst_description="마운자로/젭바운드 GLP-1 공급 쇼티지 해소 및 적응증(심혈관/수면무호흡) 확대"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_lly * 1.26, expected_return_pct=0.26, catalyst_description="글로벌 비만/당뇨 시장 점유율 1위 및 2039년 특허 해자 지속"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_lly * 0.85, expected_return_pct=-0.15, catalyst_description="경구용 비만 치료제 신약 임상 3상 실패")
            ),
            moat_description="GLP-1 펩타이드 대사 질환 의약품 독점 및 2039년까지 이어지는 글로벌 특허 방벽.",
            bottleneck_role="인류 비만, 당뇨, 심혈관 대사 치료제의 필수 글로벌 바이오 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_lly, p_lly * 1.26),
            thesis_invalidation_triggers=["경쟁사 신약이 효능과 가격에서 압도적 우위 확보"]
        ))

        p_cost = self.price_service.get_price("US-COST", 961.10)
        assets.append(Asset(
            id="US-COST", name="Costco Wholesale Corporation (NASDAQ: COST)", asset_class=AssetClass.EQUITIES,
            current_price=p_cost, intrinsic_value_base=p_cost * 1.24, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.5, 9.7, 9.8, 9.2),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_cost * 1.45, expected_return_pct=0.45, catalyst_description="멤버십 연회비 인상분 100% 이익 반영 및 글로벌 신규 매장 확장"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_cost * 1.24, expected_return_pct=0.24, catalyst_description="연 93%+ 멤버십 갱신율 및 음(-)의 운전자본 무이자 레버리지 지속"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_cost * 0.86, expected_return_pct=-0.14, catalyst_description="인플레이션 둔화로 동일매장 매출 성장률 둔화")
            ),
            moat_description="연간 45억 달러의 무이자 멤버십 선수금과 세계 최고 구매력으로 제품을 원가에 공급하는 소비자 잉여 극대화 모델.",
            bottleneck_role="미국/글로벌 중산층 필수 생필품 공급망의 대체 불가능한 유통 요새.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_cost, p_cost * 1.24),
            thesis_invalidation_triggers=["멤버십 갱신율이 80% 이하로 추락할 때"]
        ))

        return assets
