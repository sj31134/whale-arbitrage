"""
Real Estate Screener: Institutional research and valuation for Prime Land and Residential Assets.
Expanded across Super Prime Seoul, Sub-10억 Seoul/Gyeonggi Wealth Ladders, and Chungcheong Provincial Industrial Hubs (천안, 대전, 청주, 세종, 오송).
"""
from typing import List
from ..core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from ..core.valuation import ValuationEngine
from ..core.scoring_engine import ScoringEngine
from ..data_pipeline.live_price_service import LivePriceService


class RealEstateScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_real_estate_universe(self) -> List[Asset]:
        assets: List[Asset] = []

        # =========================================================================
        # 1. Super Prime Seoul Land Monopolies (Index = 100.0)
        # =========================================================================
        super_prime_configs = [
            ("RE-HANNAM-UN", "Hannam UN Village Prime Land (Seoul)", 100.0, 135.0, 10.0, 10.0, 10.0, 10.0, 9.8,
             "배산임수 남향 한강 조망 반도형 폐쇄 지형, 전액 현금 매수 Top 0.01% 자산가 군집.", "대한민국 상위 0.01% 폐쇄형 주거 지대 독점."),
            ("RE-APGUJEONG", "Apgujeong Hyundai Reconstruction Land Share (Seoul)", 100.0, 125.0, 9.9, 9.8, 9.9, 9.9, 9.6,
             "압구정 특별계획구역 70층 재건축 신통기획 확정, 강남 8학군 및 인프라 독점.", "대한민국 부의 정점이자 불패의 한강변 평지 대지지분."),
            ("RE-BANPO-ONE", "Banpo Han Riverfront Trophy Land Share (Seoul)", 100.0, 120.0, 9.8, 9.7, 9.8, 9.8, 9.5,
             "신반포 한강변 랜드마크 아파트 대지지분.", "강남 핵심 주거 인프라 및 신축 프리미엄 요새."),
            ("RE-SEONGSU-IT", "Seongsu Prime Waterfront & IT Hub Land (Seoul)", 100.0, 135.0, 9.8, 9.7, 9.7, 9.8, 9.8,
             "성수 전략정비구역 50층+ 초고층 한강변 재개발 및 IT 유니콘 밸리.", "강남을 마주보는 한강 북안 최고의 차세대 메가 상업/주거 지대."),
            ("RE-YEOUIDO-FIN", "Yeouido Financial Hub Reconstruction Land (Seoul)", 100.0, 125.0, 9.7, 9.6, 9.7, 9.8, 9.5,
             "여의도 국제금융특구 및 시범/한양아파트 70층 재건축 대지지분.", "한국 금융 심장부의 주거/금융 복합 토지 요새."),
            ("RE-YONGSAN-HUB", "Yongsan Park & Station Master Commercial Land (Seoul)", 100.0, 140.0, 9.9, 9.8, 9.8, 9.9, 9.8,
             "51조 원 용산국제업무지구 및 용산민족공원 중심축 상업/주거 대지지분.", "서울 도심 최대 복합개발 및 신분당선/GTX 쿼드러플 교통 허브."),
            ("RE-HANNAM-NT", "Hannam New Town 3/4/5 District Land Share (Seoul)", 100.0, 135.0, 9.9, 9.8, 9.9, 9.9, 9.7,
             "한남뉴타운 한강 조망 하이엔드 대단지 입주권 대지지분.", "용산공원과 한강을 품은 서울 최대 고급 주거 타운."),
            ("RE-JAMSIL-JU5", "Jamsil Jugong 5 Reconstruction Land (Seoul)", 100.0, 128.0, 9.7, 9.6, 9.8, 9.7, 9.6,
             "잠실역 70층 랜드마크 재건축 및 잠실 MICE 스포츠/MICE 복합단지 배후.", "송파구 최고 입지의 대단지 평지 대지지분."),
            ("RE-EUNMA-DAECHI", "Daechi Eunma Reconstruction Land Share (Seoul)", 100.0, 122.0, 9.8, 9.9, 9.7, 9.8, 9.2,
             "대치동 학원가 사거리 중심축 재건축 대지지분.", "대한민국 사교육 1번지의 영구적 학군 수요 독점 요새."),
            ("RE-MOKDONG-NEW", "Mokdong 1-14 Reconstruction Land (Seoul)", 100.0, 125.0, 9.6, 9.7, 9.6, 9.7, 9.3,
             "목동 신시가지 전용면적 대비 대지지분율 110%+ 역대급 지분율.", "서남권 최대 학군지 및 5만 가구 매머드 뉴타운 재건축."),
        ]

        for aid, aname, cp, iv, s1, s2, s3, s4, s5, moat, role in super_prime_configs:
            assets.append(Asset(
                id=aid, name=aname, asset_class=AssetClass.REAL_ESTATE,
                current_price=cp, intrinsic_value_base=iv, tier=AssetTier.CORE,
                skill_scores=self.scoring_engine.evaluate_universal_skills(s1, s2, s3, s4, s5),
                scenarios=ScenarioProfile(
                    bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=cp * 1.55, expected_return_pct=0.55, catalyst_description="신속통합기획 인허가 완료 및 신고가 경신"),
                    base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv, expected_return_pct=0.28, catalyst_description="서울 1급지 희소성 및 토지 공시지가 연 8% 복리 상승"),
                    bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=cp * 0.90, expected_return_pct=-0.10, catalyst_description="부동산 경기 침체 시에도 전액 현금 매수층으로 가격 지지 방어")
                ),
                moat_description=moat, bottleneck_role=role,
                margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(cp, iv),
                thesis_invalidation_triggers=["서울 인구의 영구 붕괴 또는 수도 이전"]
            ))

        # =========================================================================
        # 2. Sub-10억 서울·수도권 및 충청권 핵심 자산 사다리 (매매가 억원 기준)
        # =========================================================================
        ladder_configs = [
            # 서울·수도권 사다리
            ("RE-NOWON-RECON", "Nowon Sanggye Jugong Reconstruction Land (Seoul / 6.8억)", 6.8, 11.5, 9.9, 9.9, 9.9, 9.8, 9.9,
             "전용면적 대비 대지지분율 최상급, 신축 공사비 이하의 서울 토지 대지지분 헐값 상태. 1주택 비과세 갭투자(3억) 최적지.", "강북 최대 3만 세대 미니 신도시 재건축 사다리."),
            ("RE-YONGSAN-VILLA", "Yongsan Hyochang/Wonhyo Villa Land (Seoul / 8.5억)", 8.5, 12.5, 9.8, 9.8, 9.6, 9.7, 9.8,
             "51조 용산국제업무지구 배후 모아타운/신통기획 후보지 대지지분.", "서울 1급지 진입을 위한 10억 이하 유일의 용산 토지지분 통제 수단."),
            ("RE-MAPO-YEOMRI", "Mapo Yeomri/Ahyeon Redevelopment Land (Seoul / 9.2억)", 9.2, 12.2, 9.5, 9.4, 9.6, 9.6, 9.5,
             "여의도(YBD) 및 광화문(CBD) 10분 직주근접 마포 재개발 초기 입주권/지분.", "서울 3대 도심 접근성 최상위 직주근접 주거 요새."),
            ("RE-SEONGDONG-SONGJEONG", "Seongdong Songjeong/Majang Villa Land (Seoul / 7.8억)", 7.8, 10.4, 9.4, 9.5, 9.3, 9.5, 9.6,
             "성수 IT 밸리 및 한양대 배후 모아타운 정비구역 대지지분.", "성수동 확장 수혜를 가장 저렴하게 흡수하는 강북 역세권 빌라."),
            ("RE-BUNDANG-1ST", "Bundang 1st New Town Reconstruction Land (Gyeonggi / 9.2억)", 9.2, 12.2, 9.5, 9.7, 9.6, 9.7, 9.5,
             "1기 신도시 특별법 선도지구 용적률 350% 상향, 판교 테크노밸리 배후 대단지 지분.", "경기도의 강남, 판교 IT 일자리를 품은 1기 신도시 대장."),
            ("RE-PYEONGCHON-1ST", "Pyeongchon 1st New Town School District (Gyeonggi / 7.2억)", 7.2, 9.8, 9.3, 9.5, 9.4, 9.5, 9.3,
             "평촌 학원가 도보권 귀인/꿈마을 역세권 재건축 대지지분.", "경기 남부 1위 학군지 수요 기반 안정적 전세가 방어 요새."),
            ("RE-GWANGMYEONG-NT", "Gwangmyeong New Town Redevelopment Land (Gyeonggi / 7.8억)", 7.8, 10.2, 9.3, 9.4, 9.5, 9.5, 9.4,
             "7호선 철산/광명사거리 역세권, 서울 02 생활권 2.5만 가구 매머드 뉴타운 입주권.", "가산디지털단지 및 강남 직통 7호선 베드타운 1위."),
            ("RE-SUWON-YEONGTONG", "Suwon Yeongtong Maetan Jugong (Gyeonggi / 6.2억)", 6.2, 8.5, 9.2, 9.4, 9.3, 9.4, 9.5,
             "삼성전자 본사 영통 디지털시티 도보 5분 직주근접 재건축 대지지분.", "삼성전자 연구원 고소득 탄탄한 배후 수요 기반 재건축 킹핀."),

            # 충청권 반도체·배터리·바이오·행정수도 핵심 클러스터
            ("RE-CHEONAN-BULDANG", "Cheonan Buldang New Town 84㎡ (Chungnam / 7.2억)", 7.2, 9.6, 9.2, 9.3, 9.4, 9.3, 9.2,
             "삼성디스플레이 탕정 + 삼성전자 온양 패키징 팹 배후, 충남 1위 불당동 학군지 (전세 4.8억 / 갭 2.4억).", "충청권 최고 소득 직주근접 및 학군 불패 지대."),
            ("RE-DAEJEON-DUNSAN", "Daejeon Dunsan Croba/Mokryun 84㎡ (Daejeon / 8.8억)", 8.8, 11.8, 9.4, 9.5, 9.5, 9.4, 9.3,
             "대전 둔산동 사교육 1번지 학원가 도보권, 30년 재건축 연한 도래 (전세 5.4억 / 갭 3.4억).", "카이스트 및 대덕연구단지 고소득 연구원 배후 학군 대장."),
            ("RE-CHEONGJU-OCHANG", "Cheongju Ochang Battery Valley 84㎡ (Chungbuk / 4.8억)", 4.8, 6.6, 8.9, 9.1, 9.2, 9.0, 9.1,
             "LG에너지솔루션 오창 마더팩토리 + 에코프로비엠 + 방사광가속기 배후 (전세 3.4억 / 갭 1.4억).", "K-배터리 글로벌 생산 중심축 및 고소득 일자리 배후지."),
            ("RE-SEJONG-SAETDEUM", "Sejong 2-2 Saetdeum Village 84㎡ (Sejong / 6.8억)", 6.8, 9.0, 9.1, 9.2, 9.3, 9.2, 9.0,
             "국회 세종의사당 및 중앙행정타운 직주근접 대단지 (전세 3.0억 / 갭 3.8억).", "대한민국 행정수도 완성 및 광역 교통망 중심축."),
            ("RE-OSONG-BIO", "Chungbuk Osong K-Bio Square 84㎡ (Chungbuk / 4.2억)", 4.2, 5.8, 8.8, 9.0, 9.1, 8.9, 9.0,
             "질병관리청, 식약처 및 국내 1위 바이오 CDMO 클러스터 직주근접 (전세 2.8억 / 갭 1.4억).", "K-바이오 국가첨단전략산업 특화단지 핵심 주거지.")
        ]

        for aid, aname, cp, iv, s1, s2, s3, s4, s5, moat, role in ladder_configs:
            assets.append(Asset(
                id=aid, name=aname, asset_class=AssetClass.REAL_ESTATE,
                current_price=cp, intrinsic_value_base=iv, tier=AssetTier.CORE,
                skill_scores=self.scoring_engine.evaluate_universal_skills(s1, s2, s3, s4, s5),
                scenarios=ScenarioProfile(
                    bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=cp * 1.65, expected_return_pct=0.65, catalyst_description="정비구역 지정 고시 또는 반도체/배터리 대규모 증설로 호가 급등"),
                    base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=iv, expected_return_pct=0.35, catalyst_description="지역 일자리 및 1주택 비과세 갭투자 전세가율 상승"),
                    bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=cp * 0.88, expected_return_pct=-0.12, catalyst_description="지방 부동산 침체 시에도 탄탄한 직주근접 전세 보증금 하방 지지")
                ),
                moat_description=moat, bottleneck_role=role,
                margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(cp, iv),
                thesis_invalidation_triggers=["해당 산업단지의 대규모 철수 또는 정비구역 직권 취소"]
            ))

        # =========================================================================
        # 3. US Real Estate & Infrastructure Land
        # =========================================================================
        p_dc = self.price_service.get_price("RE-DATA-CENTER-LAND", 100.0)
        assets.append(Asset(
            id="RE-DATA-CENTER-LAND", name="Grid-Connected 500MW Data Center Land (US PJM/ERCOT)", asset_class=AssetClass.REAL_ESTATE,
            current_price=p_dc, intrinsic_value_base=p_dc * 1.35, tier=AssetTier.SATELLITE,
            skill_scores=self.scoring_engine.evaluate_universal_skills(9.6, 9.9, 9.8, 9.8, 9.8),
            scenarios=ScenarioProfile(
                bull_case=ScenarioOutcome("Bull (30%)", 0.30, target_price=p_dc * 1.80, expected_return_pct=0.80, catalyst_description="빅테크 하이퍼스케일러 500MW 부지 임대권 매각"),
                base_case=ScenarioOutcome("Base (50%)", 0.50, target_price=p_dc * 1.35, expected_return_pct=0.35, catalyst_description="PJM 변전소 직연결 송전망 프리미엄 반영"),
                bear_case=ScenarioOutcome("Bear (20%)", 0.20, target_price=p_dc * 0.85, expected_return_pct=-0.15, catalyst_description="지역 전력망 수전 허가 반려")
            ),
            moat_description="500MW 이상의 초고압 전력 인입망(Interconnection Queue) 허가를 이미 확보한 희소 토지.",
            bottleneck_role="AI 기가와트급 데이터센터 착공을 위한 단일 물리적 토지 병목.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_dc, p_dc * 1.35),
            thesis_invalidation_triggers=["PJM 송전망 계통 연계 인허가 전면 취소"]
        ))

        return assets
