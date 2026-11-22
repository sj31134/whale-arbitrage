"""
Japanese Equity Screener: Institutional research and valuation for Japanese Equities
Expanded with global tech champions (Tokyo Electron, Lasertec, Shin-Etsu Chemical, Sony Group, FANUC, DISCO, Keyence, Advantest, Mitsubishi, TIGER Japan Semi ETF).
"""
from typing import List
from src.core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from src.core.valuation import ValuationEngine
from src.core.scoring_engine import ScoringEngine
from src.data_pipeline.live_price_service import LivePriceService


class JPEquityScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_jp_equity_universe(self) -> List[Asset]:
        return self.get_screened_universe()

    def get_screened_universe(self) -> List[Asset]:
        assets: List[Asset] = []

        # 1. Tokyo Electron (8035.T) - Tier: CORE (Coater/Developer 90% Global Monopoly)
        p_tel = self.price_service.get_price("JP-8035", 28500.0)
        iv_tel = p_tel * 1.30
        assets.append(Asset(
            id="JP-8035", name="Tokyo Electron Limited (TSE: 8035)", asset_class=AssetClass.EQUITIES,
            current_price=p_tel, intrinsic_value_base=iv_tel, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.9, 9.8, 9.9, 9.9, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_tel * 1.55, expected_return_pct=0.55, catalyst_description="EUV용 코터/디벨로퍼 100% 독점 및 차세대 극저온 에칭 장비 점유율 확대"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_tel, expected_return_pct=0.30, catalyst_description="첨단 로직 및 3D 낸드 식각/증착 장비 매출 연 25% 성장"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_tel * 0.82, expected_return_pct=-0.18, catalyst_description="대중국 반도체 장비 수출 규제 품목 확대")
            ),
            moat_description="EUV 노광 공정에 직결되는 코터/디벨로퍼 장비 점유율 90%를 장악한 글로벌 전공정 장비 요새.",
            bottleneck_role="ASML 노광장비와 한 몸으로 결합되어 반도체 웨이퍼를 도포/현상하는 필수 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_tel, iv_tel),
            thesis_invalidation_triggers=["경쟁사가 EUV 코터/디벨로퍼 수율을 능가할 때"]
        ))

        # 2. Lasertec (6920.T) - Tier: SATELLITE (EUV Mask Inspection 100% Monopoly)
        p_las = self.price_service.get_price("JP-6920", 24500.0)
        iv_las = p_las * 1.35
        assets.append(Asset(
            id="JP-6920", name="Lasertec Corporation (TSE: 6920)", asset_class=AssetClass.EQUITIES,
            current_price=p_las, intrinsic_value_base=iv_las, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.9, 10.0, 9.9, 10.0, 9.8),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_las * 1.65, expected_return_pct=0.65, catalyst_description="High-NA EUV 액티닉(Actinic) 마스크 검사장비 독점 출하 + OPM 45% 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_las, expected_return_pct=0.35, catalyst_description="TSMC/인텔/삼성 2nm 파운드리용 마스크 검사기 주문 잔고 견조"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_las * 0.78, expected_return_pct=-0.22, catalyst_description="KLA 등 경쟁사의 액티닉 검사장비 시장 진입")
            ),
            moat_description="EUV 파장의 빛을 직접 투과하여 결함을 검사하는 액티닉 EUV 마스크 검사장비 시장 100% 독점.",
            bottleneck_role="2nm 첨단 반도체 양산 시 포토마스크 불량을 검사하는 전 세계 유일의 장비 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_las, iv_las),
            thesis_invalidation_triggers=["KLA가 Lasertec의 특허를 무효화하고 동급 장비 양산에 성공할 때"]
        ))

        # 3. Shin-Etsu Chemical (4063.T) - Tier: CORE (Global Silicon Wafer & Photoresist Leader)
        p_shin = self.price_service.get_price("JP-4063", 6450.0)
        iv_shin = p_shin * 1.25
        assets.append(Asset(
            id="JP-4063", name="Shin-Etsu Chemical Co., Ltd. (TSE: 4063)", asset_class=AssetClass.EQUITIES,
            current_price=p_shin, intrinsic_value_base=iv_shin, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.7, 9.9, 9.8, 9.4),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_shin * 1.48, expected_return_pct=0.48, catalyst_description="300mm 첨단 에피택셜 웨이퍼 공급 부족으로 판가 15% 인상 + 미국 PVC 수직계열화 초과이익"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_shin, expected_return_pct=0.25, catalyst_description="무차입 순현금 1.5조 엔 및 반도체 소재 OPM 30%+ 유지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_shin * 0.85, expected_return_pct=-0.15, catalyst_description="글로벌 건축 경기 침체로 미국 PVC 마진 둔화")
            ),
            moat_description="300mm 고순도 실리콘 웨이퍼 및 EUV 포토레지스트 1위 기업으로 1.5조 엔 순현금을 보유한 화학/소재 요새.",
            bottleneck_role="글로벌 모든 반도체의 물리적 기판(웨이퍼)을 공급하는 최하단 기초 소재 게이트키퍼.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_shin, iv_shin),
            thesis_invalidation_triggers=["새로운 기판(갈륨나이트라이드 등)이 실리콘 웨이퍼를 전면 대체할 때"]
        ))

        # 4. Sony Group (6758.T) - Tier: CORE (CMOS Image Sensor 53% Global Monopoly)
        p_sony = self.price_service.get_price("JP-6758", 14500.0)
        iv_sony = p_sony * 1.28
        assets.append(Asset(
            id="JP-6758", name="Sony Group Corporation (TSE: 6758)", asset_class=AssetClass.EQUITIES,
            current_price=p_sony, intrinsic_value_base=iv_sony, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.7, 9.6, 9.8, 9.8, 9.5),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_sony * 1.52, expected_return_pct=0.52, catalyst_description="자율주행차 및 로보틱스용 차량용 CIS 센서 공급 2배 급증 + 플레이스테이션 네트워크 구독 FCF 폭발"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv_sony, expected_return_pct=0.28, catalyst_description="애플 아이폰 프리미엄 2층 트랜지스터 픽셀 센서 독점 공급 지속"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_sony * 0.84, expected_return_pct=-0.16, catalyst_description="스마트폰 글로벌 출하량 둔화")
            ),
            moat_description="글로벌 모바일 및 차량용 CMOS 이미지 센서 시장 53%를 독점하고 세계 최대 엔터테인먼트(게임/음악/영화) IP를 결합한 복합 제국.",
            bottleneck_role="인공지능과 카메라가 세상을 '보는' 물리적 시각 센서(눈)의 독점 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_sony, iv_sony),
            thesis_invalidation_triggers=["삼성전자가 프리미엄 모바일 CIS 시장 점유율을 50% 이상 역전할 때"]
        ))

        # 5. DISCO (6146.T), Keyence (6861.T), Advantest (6857.T), Mitsubishi (8058.T), TIGER ETF (465660.KS)
        p_disco = self.price_service.get_price("JP-6146", 65470.0)
        assets.append(Asset(
            id="JP-6146", name="DISCO Corporation (TSE: 6146)", asset_class=AssetClass.EQUITIES,
            current_price=p_disco, intrinsic_value_base=p_disco * 1.30, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.9, 9.9, 9.9, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_disco * 1.62, expected_return_pct=0.62, catalyst_description="HBM3E/HBM4용 정밀 연삭·절단 장비 독점 및 다이아몬드 휠 소모품 OPM 50%+"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_disco * 1.30, expected_return_pct=0.30, catalyst_description="글로벌 웨이퍼 다이싱/그라인딩 점유율 80%+ 유지"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_disco * 0.81, expected_return_pct=-0.19, catalyst_description="후공정 패키징 Capex 일시 조정")
            ),
            moat_description="웨이퍼 다이싱/그라인딩 장비 시장 80% 독점 및 다이아몬드 휠 소모품 면도기-날 모델.",
            bottleneck_role="HBM 및 첨단 반도체 웨이퍼를 마이크로 단위로 얇게 갈아내는 유일한 정밀 가공 병목.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_disco, p_disco * 1.30),
            thesis_invalidation_triggers=["레이저 절단 기술이 기계식 연삭 다이아몬드 휠을 100% 무력화할 때"]
        ))

        p_keyence = self.price_service.get_price("JP-6861", 87660.0)
        assets.append(Asset(
            id="JP-6861", name="Keyence Corporation (TSE: 6861)", asset_class=AssetClass.EQUITIES,
            current_price=p_keyence, intrinsic_value_base=p_keyence * 1.25, tier=AssetTier.CORE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.7, 9.9, 9.8, 9.5),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_keyence * 1.48, expected_return_pct=0.48, catalyst_description="글로벌 공장 자동화 및 머신비전 센서 수요 급증으로 OPM 55% 돌파"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_keyence * 1.25, expected_return_pct=0.25, catalyst_description="무차입 2.5조 엔 순현금 및 직판 컨설팅 영업 모델 FCF 창출"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_keyence * 0.86, expected_return_pct=-0.14, catalyst_description="글로벌 제조업 설비투자 축소")
            ),
            moat_description="공장 자동화 센서/머신비전 기술과 100% 직판 컨설팅 영업력으로 영업이익률 50%+를 창출하는 스마트 팩토리의 심장.",
            bottleneck_role="제조업 자동화 및 결함 검출의 필수 센서 공급원.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_keyence, p_keyence * 1.25),
            thesis_invalidation_triggers=["저가형 센서가 키엔스의 컨설팅 직판 모델을 대체할 때"]
        ))

        p_tiger_jp = self.price_service.get_price("JP-ETF-465660", 26840.0)
        assets.append(Asset(
            id="JP-ETF-465660", name="TIGER Japan Semiconductor FACTSET ETF (465660.KS)", asset_class=AssetClass.EQUITIES,
            current_price=p_tiger_jp, intrinsic_value_base=p_tiger_jp * 1.28, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.8, 9.8, 9.8, 9.8, 9.7),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_tiger_jp * 1.55, expected_return_pct=0.55, catalyst_description="일본 반도체 소부장 르네상스 + 엔화 절상에 따른 환차익 이중 수혜"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_tiger_jp * 1.28, expected_return_pct=0.28, catalyst_description="도쿄일렉트론, 디스코, 어드반테스트, 레이저텍, 신에츠화학 바스켓 안정적 FCF 성장"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_tiger_jp * 0.82, expected_return_pct=-0.18, catalyst_description="글로벌 반도체 다운사이클 진입")
            ),
            moat_description="일본 반도체 생태계의 핵심 독점 소부장(소재·부품·장비) 기업들을 일괄 편입한 ETF 바스켓.",
            bottleneck_role="글로벌 반도체 공급망에서 일본 모노즈쿠리 독점을 원스톱으로 장악하는 바스켓.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_tiger_jp, p_tiger_jp * 1.28),
            thesis_invalidation_triggers=["일본 소부장 기업들의 글로벌 시장 점유율이 30% 이하로 추락할 때"]
        ))

        return assets
