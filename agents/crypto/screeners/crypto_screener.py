"""
Crypto & Digital Asset Screener: Institutional research, valuation, and live price ingestion for Cryptocurrencies,
Layer 1 settlement protocols, and Real World Asset (RWA) tokenization engines.
"""
from typing import List
from src.core.asset import (
    Asset, AssetClass, AssetTier, UniversalSkillScores,
    ScenarioProfile, ScenarioOutcome
)
from src.core.valuation import ValuationEngine
from src.core.scoring_engine import ScoringEngine
from src.data_pipeline.live_price_service import LivePriceService


class CryptoScreener:
    def __init__(self):
        self.valuation_engine = ValuationEngine()
        self.scoring_engine = ScoringEngine()
        self.price_service = LivePriceService()

    def get_crypto_universe(self) -> List[Asset]:
        assets: List[Asset] = []

        # 1. Bitcoin (BTC) - Tier: SATELLITE / HARD ASSET
        p_btc = self.price_service.get_price("CRYPTO-BTC", 62956.0)
        iv_btc = p_btc * 1.35
        btc_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.8,
            inelasticity_score=10.0,
            buyer_quality_score=9.4,
            walled_garden_score=9.8,
            spillover_score=9.5
        )
        btc_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome(
                "Bull (30%)", 0.30, target_price=p_btc * 1.75, expected_return_pct=0.75,
                catalyst_description="글로벌 중앙은행 및 미국 전략준비자산 법제화로 기관 자금 수천억 달러 유입"
            ),
            base_case=ScenarioOutcome(
                "Base (50%)", 0.50, target_price=iv_btc, expected_return_pct=0.35,
                catalyst_description="현물 ETF 순유입 지속 및 반감기 공급 충격으로 완만한 금(Gold) 시총 20% 추격"
            ),
            bear_case=ScenarioOutcome(
                "Bear (20%)", 0.20, target_price=p_btc * 0.76, expected_return_pct=-0.24,
                catalyst_description="미국 및 G7 규제 당국의 양도세 인상 및 테더(USDT) 준비금 감사 리스크 발생"
            )
        )
        assets.append(Asset(
            id="CRYPTO-BTC",
            name="Bitcoin (BTC / Digital Hard Reserve)",
            asset_class=AssetClass.CRYPTO_RWA,
            current_price=p_btc,
            intrinsic_value_base=iv_btc,
            tier=AssetTier.SATELLITE,
            skill_scores=btc_scores,
            scenarios=btc_scenarios,
            moat_description="2,100만 개 공급 한도를 가진 무국적 디지털 불변 화폐이자 글로벌 법정통화 희석의 절대적 헤지 수단.",
            bottleneck_role="검열 불가능한 글로벌 탈중앙화 가치 저장 및 결제 인프라.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_btc, iv_btc),
            thesis_invalidation_triggers=[
                "SHA-256 암호학적 해시 알고리즘의 양자컴퓨터에 의한 치명적 붕괴",
                "핵심 채굴 풀 51% 담합을 통한 거래 검열 성공"
            ]
        ))

        # 2. Ethereum (ETH) - Tier: SATELLITE
        p_eth = self.price_service.get_price("CRYPTO-ETH", 1879.0)
        iv_eth = p_eth * 1.30
        eth_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=9.1,
            inelasticity_score=9.2,
            buyer_quality_score=9.3,
            walled_garden_score=9.5,
            spillover_score=9.6
        )
        eth_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome(
                "Bull (30%)", 0.30, target_price=p_eth * 1.65, expected_return_pct=0.65,
                catalyst_description="월가 대형 은행의 RWA(국채/사모펀드) 온체인 토큰화 폭증 및 스테이킹 ETF 허용"
            ),
            base_case=ScenarioOutcome(
                "Base (50%)", 0.50, target_price=iv_eth, expected_return_pct=0.30,
                catalyst_description="Layer 2 롤업(L2) 수수료 소각 및 디파이(DeFi) 총예치자산(TVL) 견조한 성장"
            ),
            bear_case=ScenarioOutcome(
                "Bear (20%)", 0.20, target_price=p_eth * 0.78, expected_return_pct=-0.22,
                catalyst_description="솔라나 등 고성능 단일 체인으로의 개발자 및 앱 생태계 이탈 가속화"
            )
        )
        assets.append(Asset(
            id="CRYPTO-ETH",
            name="Ethereum (ETH / Global Settlement Layer)",
            asset_class=AssetClass.CRYPTO_RWA,
            current_price=p_eth,
            intrinsic_value_base=iv_eth,
            tier=AssetTier.SATELLITE,
            skill_scores=eth_scores,
            scenarios=eth_scenarios,
            moat_description="스마트 컨트랙트와 RWA(실물자산 토큰화) 생태계의 절대적 글로벌 분산 결제 레이어.",
            bottleneck_role="디지털 금융 및 자산 토큰화의 글로벌 신뢰 및 완결성 보증 인프라.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_eth, iv_eth),
            thesis_invalidation_triggers=[
                "지분증명(PoS) 프로토콜의 대형 슬래싱 버그 또는 치명적 합의 결함",
                "SEC의 이더리움 증권성 재분류로 인한 거래 전면 규제"
            ]
        ))

        # 3. Solana (SOL) - Tier: SATELLITE
        p_sol = self.price_service.get_price("CRYPTO-SOL", 75.17)
        iv_sol = p_sol * 1.35
        sol_scores = self.scoring_engine.evaluate_universal_skills(
            decomposition_score=8.5,
            inelasticity_score=8.8,
            buyer_quality_score=9.1,
            walled_garden_score=9.2,
            spillover_score=9.7
        )
        sol_scenarios = ScenarioProfile(
            bull_case=ScenarioOutcome(
                "Bull (30%)", 0.30, target_price=p_sol * 1.70, expected_return_pct=0.70,
                catalyst_description="파이어댄서(Firedancer) 클라이언트 가동으로 10만 TPS 달성, 글로벌 결제망(비자/쇼피파이) 메인넷 안착"
            ),
            base_case=ScenarioOutcome(
                "Base (50%)", 0.50, target_price=iv_sol, expected_return_pct=0.35,
                catalyst_description="AI 에이전트 마이크로 결제 및 탈중앙 거래소(DEX) 점유율 1위 고착화"
            ),
            bear_case=ScenarioOutcome(
                "Bear (20%)", 0.20, target_price=p_sol * 0.75, expected_return_pct=-0.25,
                catalyst_description="네트워크 다운타임 재발 및 신규 L1 체인과의 유동성 경쟁 격화"
            )
        )
        assets.append(Asset(
            id="CRYPTO-SOL",
            name="Solana (SOL / High-Throughput Agent Layer)",
            asset_class=AssetClass.CRYPTO_RWA,
            current_price=p_sol,
            intrinsic_value_base=iv_sol,
            tier=AssetTier.SATELLITE,
            skill_scores=sol_scores,
            scenarios=sol_scenarios,
            moat_description="초당 수만 건의 트랜잭션과 수밀리초 레이턴시를 제공하는 온체인 나스닥이자 AI 에이전트 결제망.",
            bottleneck_role="실시간 고속 분산 컴퓨팅 및 소액 결제(Micropayments) 인프라.",
            margin_of_safety_pct=self.valuation_engine.calculate_margin_of_safety(p_sol, iv_sol),
            thesis_invalidation_triggers=[
                "네트워크 24시간 이상 연속 정지 사고 재발",
                "인플레이션 및 밸리데이터 중앙화로 인한 보안성 훼손"
            ]
        ))

        return assets
