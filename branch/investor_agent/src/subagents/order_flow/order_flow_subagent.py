"""
Order Flow & Microstructure Short-Term Trading Subagent:
Orchestrates global order flow disaggregation (KRX & US), dynamic discovery of new candidate stocks,
$10 Early Breakout Inflection Analysis (PLTR/TSLA/RKLB/ASTS/IREN DNA), support/resistance extraction,
causal network forecasting, independent third-party risk auditing, and tactical execution.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .models import (
    ActorType, SupportResistanceType, TradingStrategyType, MarketType,
    StockMicrostructureProfile, ShortTermPriceForecast,
    MicrostructureTradeDecision, ActorDynamicVariables, CandidateStockItem
)
from .flow_disaggregator import OrderFlowDisaggregator
from .support_resistance_engine import SupportResistanceEngine
from .impact_network_engine import ImpactNetworkEngine
from .dynamic_flow_updater import DynamicFlowUpdater
from .trading_engine import MicrostructureTradingEngine
from .universe_collector import UniverseCollector
from .risk_auditor import ThirdPartyRiskAuditor
from .ten_dollar_inflection_engine import TenDollarInflectionEngine, InflectionScorecard
from ...data_pipeline.price_sanity_checker import PriceSanityChecker


class OrderFlowSubagent:
    """
    Subordinate Subagent specialized in:
    1. Dynamic Universe Ingestion & Discovery (KRX and US Equities, including newly discovered breakout stocks).
    2. $10 Early Breakout Inflection Modeling (Reverse-engineering PLTR, TSLA, RKLB, ASTS, IREN).
    3. Order Flow Disaggregation (Foreigners/Offshore Hedge Funds vs Institutions vs Dark Pools vs Retail).
    4. Structural Support & Resistance calculation via Participant VWAPs & Trapped Supply.
    5. Causal Network Short-Term Price Forecasting (1D/5D) driven by Global Dynamic Variables.
    6. Third-Party Independent Risk Audit (Chief Risk Officer / Red Team Review).
    7. Execution of Asymmetric Tactical Trading conforming to Parent Investor Principles.
    """

    def __init__(self, hurdle_payoff: float = 3.0):
        self.universe_collector = UniverseCollector()
        self.disaggregator = OrderFlowDisaggregator()
        self.sr_engine = SupportResistanceEngine()
        self.network_engine = ImpactNetworkEngine()
        self.flow_updater = DynamicFlowUpdater()
        self.trading_engine = MicrostructureTradingEngine(min_payoff_ratio=hurdle_payoff)
        self.risk_auditor = ThirdPartyRiskAuditor()
        self.inflection_engine = TenDollarInflectionEngine()
        self.price_checker = PriceSanityChecker()
        self.hurdle_payoff = hurdle_payoff

    def ingest_new_candidate_stock(
        self,
        ticker: str,
        name: str,
        market: MarketType,
        sector: str,
        current_price: float,
        currency: Optional[str] = None,
        daily_volume: int = 1_000_000,
        daily_turnover: float = 50_000_000_000,
        discovery_reason: str = "신규 수급 및 모멘텀 이상 급증 감지"
    ) -> CandidateStockItem:
        """
        Dynamically ingests and registers an arbitrary new stock ticker into the subagent's tracking list.
        """
        return self.universe_collector.ingest_new_ticker(
            ticker=ticker,
            name=name,
            market=market,
            sector=sector,
            current_price=current_price,
            currency=currency,
            daily_volume=daily_volume,
            daily_turnover=daily_turnover,
            discovery_reason=discovery_reason
        )

    def analyze_stock(
        self,
        ticker: str,
        name: str,
        current_price: float,
        daily_volume: int = 1_000_000,
        daily_turnover: float = 80_000_000_000,
        market: MarketType = MarketType.KRX,
        currency: Optional[str] = None,
        sector: str = "Technology",
        raw_flow_data: Optional[Dict[str, Any]] = None,
        is_new_candidate: bool = False
    ) -> Dict[str, Any]:
        """
        Executes end-to-end microstructure & $10 inflection analysis for a single stock.
        """
        # Step 1: Disaggregate Order Flow
        profile = self.disaggregator.disaggregate_stock_flow(
            ticker=ticker,
            name=name,
            current_price=current_price,
            daily_volume=daily_volume,
            daily_turnover=daily_turnover,
            market=market,
            currency=currency,
            raw_flow_data=raw_flow_data,
            is_new_candidate=is_new_candidate
        )

        # Step 2: Calculate Exact Support & Resistance Levels
        profile = self.sr_engine.calculate_levels(profile)

        # Step 3: Network Graph Propagation & Price Forecast
        current_vars = self.flow_updater.get_latest_variables()
        forecast = self.network_engine.forecast_price_trajectory(profile, current_vars)

        # Step 4: $10 Breakout DNA Scorecard Evaluation
        inflection_card = self.inflection_engine.evaluate_candidate_inflection(
            ticker=ticker,
            name=name,
            current_price=current_price,
            market=market,
            sector=sector,
            currency=profile.currency
        )

        # Step 5: Generate Trading Decision adhering to Parent Principles & Anti-FOMO rules
        trade_decision = self.trading_engine.generate_trade_decision(profile, forecast)

        return {
            "ticker": ticker,
            "name": name,
            "market": market,
            "currency": profile.currency,
            "sector": sector,
            "is_new_candidate": is_new_candidate,
            "profile": profile,
            "forecast": forecast,
            "inflection_card": inflection_card,
            "trade_decision": trade_decision
        }

    def run_subagent_pipeline(
        self,
        market_filter: str = "all",
        include_new_candidates: bool = True,
        target_universe: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Runs the full subagent analysis across the global active universe (KRX + US + $10 Inflection Discoveries).
        """
        # Refresh dynamic variables
        dynamic_vars = self.flow_updater.refresh_flow_variables()
        self.network_engine.update_variables(dynamic_vars)

        if target_universe:
            universe_items = []
            for item in target_universe:
                mkt = item.get("market", MarketType.US if item["ticker"].isalpha() else MarketType.KRX)
                universe_items.append(CandidateStockItem(
                    ticker=item["ticker"],
                    name=item["name"],
                    market=mkt,
                    sector=item.get("sector", "General"),
                    current_price=item["price"],
                    currency=item.get("currency", "USD" if mkt == MarketType.US else "KRW"),
                    daily_volume=item.get("volume", 1_000_000),
                    daily_turnover=item.get("turnover", 50_000_000_000),
                    is_new_candidate=item.get("is_new_candidate", False)
                ))
        else:
            universe_items = self.universe_collector.get_active_universe(
                market_filter=market_filter,
                include_new_candidates=include_new_candidates
            )

        # Audit prices against 2026 live sanity checker
        price_audit = self.price_checker.audit_universe(universe_items)
        if price_audit["failed_count"] > 0:
            print(f" ⚠️ [PRICE SANITY WARNING] {price_audit['failed_count']} items flagged with price anomalies:")
            for f in price_audit["failed_items"]:
                print(f"   - {f['reason']}")
        else:
            print(f" ✅ [PRICE SANITY AUDIT PASSED] All {price_audit['passed_count']} candidate stock prices verified against 2026-08-29 live market feeds.")

        results: List[Dict[str, Any]] = []
        for item in universe_items:
            res = self.analyze_stock(
                ticker=item.ticker,
                name=item.name,
                current_price=item.current_price,
                daily_volume=item.daily_volume,
                daily_turnover=item.daily_turnover,
                market=item.market,
                currency=item.currency,
                sector=item.sector,
                is_new_candidate=item.is_new_candidate
            )
            results.append(res)

        # Generate Subagent Institutional Memo
        memo = self.generate_subagent_markdown_memo(results, dynamic_vars, market_filter)

        # Conduct Independent Third-Party Risk Audit (Chief Risk Officer / Red Team Review)
        risk_audit = self.risk_auditor.conduct_comprehensive_risk_audit(results, dynamic_vars)

        return {
            "timestamp": datetime.now().isoformat(),
            "dynamic_variables": dynamic_vars,
            "market_filter": market_filter,
            "analyzed_count": len(results),
            "newly_discovered_count": sum(1 for r in results if r["is_new_candidate"]),
            "results": results,
            "subagent_memo": memo,
            "risk_audit": risk_audit,
            "combined_report": memo + "\n\n" + risk_audit["audit_memo"]
        }

    def sync_to_knowledge_graph(self, knowledge_graph: Any, subagent_results: List[Dict[str, Any]]):
        """
        Syncs subagent order flow nodes, support/resistance edges, and new candidates into parent Knowledge Graph.
        """
        for r in subagent_results:
            ticker = r["ticker"]
            name = r["name"]
            profile: StockMicrostructureProfile = r["profile"]
            forecast: ShortTermPriceForecast = r["forecast"]
            inflection: InflectionScorecard = r["inflection_card"]
            trade: MicrostructureTradeDecision = r["trade_decision"]

            node_id = f"MICRO_{ticker}"
            knowledge_graph.add_node(
                node_id=node_id,
                node_type="MicrostructureState",
                label=f"{name} ({ticker}) [{profile.market.value}]",
                metadata={
                    "market": profile.market.value,
                    "currency": profile.currency,
                    "current_price": profile.current_price,
                    "smart_money_ratio": profile.smart_money_hand_off_ratio,
                    "expected_return_5d": forecast.expected_return_5d_pct,
                    "inflection_score": inflection.total_inflection_score,
                    "action": trade.action,
                    "payoff_ratio": trade.payoff_ratio,
                    "is_new_candidate": r["is_new_candidate"]
                }
            )

            if profile.support_levels:
                top_sup = profile.support_levels[0]
                price_str = f"{top_sup.price:,.0f}원" if profile.currency == "KRW" else f"${top_sup.price:.2f}"
                sup_id = f"SUP_{ticker}_{int(top_sup.price)}"
                knowledge_graph.add_node(
                    node_id=sup_id,
                    node_type="SupportLevel",
                    label=f"{name} 지지선: {price_str} ({top_sup.dominant_actor.value})"
                )
                knowledge_graph.add_edge(
                    source=node_id,
                    target=sup_id,
                    relation="HAS_SUPPORT_FLOOR",
                    weight=top_sup.strength_score / 10.0
                )

            if profile.resistance_levels:
                top_res = profile.resistance_levels[0]
                price_str = f"{top_res.price:,.0f}원" if profile.currency == "KRW" else f"${top_res.price:.2f}"
                res_id = f"RES_{ticker}_{int(top_res.price)}"
                knowledge_graph.add_node(
                    node_id=res_id,
                    node_type="ResistanceLevel",
                    label=f"{name} 저항선: {price_str} ({top_res.dominant_actor.value})"
                )
                knowledge_graph.add_edge(
                    source=node_id,
                    target=res_id,
                    relation="HAS_RESISTANCE_CEILING",
                    weight=top_res.strength_score / 10.0
                )

        knowledge_graph.save_graph()

    def generate_subagent_markdown_memo(
        self,
        results: List[Dict[str, Any]],
        dynamic_vars: ActorDynamicVariables,
        market_filter: str = "all"
    ) -> str:
        """
        Formats subagent results into a comprehensive multi-market institutional markdown report,
        featuring the $10 Inflection Engine and Historic Case Studies.
        """
        new_count = sum(1 for r in results if r["is_new_candidate"])
        lines = [
            "# ⚡ [Global Subagent Memo] 글로벌 수급 분해, $10 텐배거 DNA 분석 및 단기 트레이딩 전략 보고서",
            f"> **분석 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"> **대상 시장:** 한국(KRX) + 미국(NASDAQ/NYSE) | **시장 필터:** {market_filter.upper()}  ",
            f"> **분석 종목 수:** 총 {len(results)}개 종목 (**기존 {len(results)-new_count}개 + 신규 발굴 종목 {new_count}개**)  ",
            f"> **핵심 분석 프레임워크:** 과거 $10불대 텐배거(PLTR, TSLA, RKLB, ASTS, IREN) 5대 변곡점 DNA 모델링  ",
            f"> **상위 거버넌스:** Master Investor Agent (`investor-principles` 11 Principles)  ",
            "",
            "---",
            "",
            "## 1. 과거 $10불대 텐배거(PLTR·TSLA·RKLB·ASTS·IREN) 핵심 변수 역발상 분석",
            "",
            "과거 10배 이상 폭등한 주식들의 **$5~$15 초기 잠복기(Stealth Accumulation Phase)**에는 다음과 같은 5대 공통 변수 네트워크가 존재했습니다:",
            "",
            "```mermaid",
            "graph LR",
            "    P1[\"1. 물리적/기술적 대체불가 병목<br/>(Tech/Supply Bottleneck)\"] --> DNA[\"⚡ $10 텐배거 변곡점 DNA\"]",
            "    P2[\"2. 정부/빅테크 비취소성 수주잔고<br/>(Anchor Non-Cancellable Backlog)\"] --> DNA",
            "    P3[\"3. 공매도 과밀 vs 장외 다크풀 매집<br/>(Short Squeeze + Dark Pool Divergence)\"] --> DNA",
            "    P4[\"4. GAAP 흑자전환 / FCF 폭증<br/>(Profitability Crossover Velocity)\"] --> DNA",
            "    P5[\"5. 2년 이상 무차입 런웨이 / 부도위험 소멸<br/>(Zero Bankruptcy Put)\"] --> DNA",
            "```",
            "",
            "| 과거 10불대 종목 | 당시 잠복 가격대 | 폭등 배수 | 핵심 돌파 병목 (Bottleneck) | 앵커 수주 주체 | 공매도 비율 | 흑자 전환 촉매 |",
            "| :--- | :---: | :---: | :--- | :--- | :---: | :--- |",
            "| **Palantir (PLTR)** | $6.00 ~ $9.50 | **5.5x** | 엔터프라이즈 및 미 국방부 온톨로지 OS 독점 | US DoD, CIA, 미 육군 4.8억불 수주 | 9.8% | GAAP 순이익 4분기 연속 흑자 및 S&P500 편입 |",
            "| **Tesla (TSLA)** | $15.00 ~ $25.00 | **18.0x**| Model 3 양산 지옥 극복 및 기가 상하이 | 글로벌 소매 팬덤 + 배터리 수직계열화 | 28.5% | FCF 구조적 흑자 전환 및 차량 마진 25% 돌파 |",
            "| **Rocket Lab (RKLB)**| $3.80 ~ $5.20 | **3.5x** | Electron 50회 성공 + Neutron 중형 로켓 | 미 우주군(SDA) 5.15억불 위성 버스 수주 | 14.5% | Space Systems 고마진 위성 부품 매출 비중 70% |",
            "| **AST SpaceMobile (ASTS)**| $2.00 ~ $4.20 | **10.0x**| 우주 위성-스마트폰 직접 5G 연결 (Direct-to-Cell)| AT&T, Verizon 상용 독점 계약 체결 | 26.0% | FCC 독점 승인 및 Block 1 상용 발사 확정 |",
            "| **IREN (Iris Energy)**| $3.00 ~ $5.50 | **3.5x** | 510MW 재생에너지 전력망 + 차세대 수냉 AI HPC| AI 클라우드 GPU 고객사 및 엔비디아 배치 | 18.0% | 채굴 전력 자산의 AI HPC 전환 (ARR 1.5억불) |",
            "",
            "---",
            "",
            "## 2. 차세대 $5~$25 신규 발굴 종목 텐배거 DNA 스코어카드",
            "| 시장 | 종목명 (티커) | 현재가 | 섹터 | 5대 변곡점 총점 (/100) | 기대 상승 잠재력 | 핵심 변곡점 및 발굴 근거 |",
            "| :---: | :--- | :---: | :--- | :---: | :---: | :--- |"
        ]

        # Sort by inflection score descending
        sorted_by_inflection = sorted(results, key=lambda x: x["inflection_card"].total_inflection_score, reverse=True)

        for r in sorted_by_inflection:
            inf: InflectionScorecard = r["inflection_card"]
            if inf.market == MarketType.BINANCE_TOKENIZED:
                mkt_b = "🪙 24/7 Binance RWA"
            elif inf.market == MarketType.KRX:
                mkt_b = "🇰🇷 KRX"
            else:
                mkt_b = "🇺🇸 US"
            price_s = f"{inf.current_price:,.0f}원" if inf.currency == "KRW" else f"${inf.current_price:.2f}"
            score_badge = f"**{inf.total_inflection_score:.1f}점** (최우수)" if inf.total_inflection_score >= 85.0 else f"{inf.total_inflection_score:.1f}점"
            lines.append(
                f"| {mkt_b} | **{inf.name}** (`{inf.ticker}`) | {price_s} | {inf.sector} | {score_badge} | **{inf.target_upside_multiplier}** | {inf.discovery_catalyst_narrative} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. 종목별 수급 정밀 분해 & 지지/저항선 맵 (Support & Resistance Map)",
            "| 시장 | 구분 | 종목명 (티커) | 현재가 | 핵심 지지선 (세력/다크풀) | 핵심 저항선 (개인물림/감마벽) | 스마트머니 손바뀜 |",
            "| :---: | :---: | :--- | :---: | :---: | :---: | :---: |"
        ])

        for r in results:
            p: StockMicrostructureProfile = r["profile"]
            is_new = "✨ 신규발굴" if r["is_new_candidate"] else "🏛️ 기존종목"
            if p.market == MarketType.BINANCE_TOKENIZED:
                mkt_badge = "🪙 Binance RWA"
            elif p.market == MarketType.KRX:
                mkt_badge = "🇰🇷 KRX"
            else:
                mkt_badge = "🇺🇸 US"
            
            if p.currency == "KRW":
                p_str = f"{p.current_price:,.0f}원"
                sup_str = f"{p.support_levels[0].price:,.0f}원 ({p.support_levels[0].distance_from_current_pct:+.1f}%)" if p.support_levels else "N/A"
                res_str = f"{p.resistance_levels[0].price:,.0f}원 ({p.resistance_levels[0].distance_from_current_pct:+.1f}%)" if p.resistance_levels else "N/A"
            else:
                p_str = f"${p.current_price:,.2f}"
                sup_str = f"${p.support_levels[0].price:,.2f} ({p.support_levels[0].distance_from_current_pct:+.1f}%)" if p.support_levels else "N/A"
                res_str = f"${p.resistance_levels[0].price:,.2f} ({p.resistance_levels[0].distance_from_current_pct:+.1f}%)" if p.resistance_levels else "N/A"

            lines.append(
                f"| {mkt_badge} | `{is_new}` | **{p.name}** (`{p.ticker}`) | {p_str} | {sup_str} | {res_str} | {p.smart_money_hand_off_ratio:+.2f} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 4. 단기 트레이딩 실행 및 시그널링 (Microstructure Execution Decisions)",
            "| 시장 | 종목명 | 전략 유형 | 포지션 액션 | 진입가 (Entry) | 목표가 (Target) | 손절가 (Stop-Loss) | 손익비 (Payoff) | 추천비중 |",
            "| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
        ])

        for r in results:
            d: MicrostructureTradeDecision = r["trade_decision"]
            if d.market == MarketType.BINANCE_TOKENIZED:
                mkt_badge = "🪙 24/7 RWA"
            elif d.market == MarketType.KRX:
                mkt_badge = "🇰🇷"
            else:
                mkt_badge = "🇺🇸"
            action_badge = f"🟢 **{d.action}**" if "BUY" in d.action else f"⚪ {d.action}"

            
            if d.currency == "KRW":
                e_str = f"{d.entry_price:,.0f}원"
                t_str = f"{d.target_price:,.0f}원"
                s_str = f"{d.stop_loss_price:,.0f}원"
            else:
                e_str = f"${d.entry_price:,.2f}"
                t_str = f"${d.target_price:,.2f}"
                s_str = f"${d.stop_loss_price:,.2f}"

            lines.append(
                f"| {mkt_badge} | **{d.name}** (`{d.ticker}`) | {d.strategy.value} | {action_badge} | {e_str} | {t_str} | {s_str} | **{d.payoff_ratio:.1f}x** | {d.recommended_position_pct*100:.1f}% |"
            )

        return "\n".join(lines)
