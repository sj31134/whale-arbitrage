"""
Unit tests for Order Flow & Microstructure Short-Term Trading Subagent across KRX & US Equities.
"""
import sys
import unittest
from pathlib import Path

# Add branch/investor_agent to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.subagents.order_flow import (
    ActorType, SupportResistanceType, TradingStrategyType, MarketType,
    OrderFlowDisaggregator, SupportResistanceEngine,
    ImpactNetworkEngine, DynamicFlowUpdater, MicrostructureTradingEngine,
    OrderFlowSubagent, ActorDynamicVariables, UniverseCollector
)
from src.agent.investor_agent_runner import InvestorAgentRunner


class TestOrderFlowSubagent(unittest.TestCase):

    def setUp(self):
        self.disaggregator = OrderFlowDisaggregator()
        self.sr_engine = SupportResistanceEngine()
        self.network_engine = ImpactNetworkEngine()
        self.updater = DynamicFlowUpdater()
        self.trading_engine = MicrostructureTradingEngine(min_payoff_ratio=3.0)
        self.subagent = OrderFlowSubagent(hurdle_payoff=3.0)

    def test_kr_order_flow_disaggregation(self):
        profile = self.disaggregator.disaggregate_stock_flow(
            ticker="005930",
            name="삼성전자",
            current_price=82500.0,
            daily_volume=10_000_000,
            daily_turnover=825_000_000_000,
            market=MarketType.KRX
        )
        self.assertEqual(profile.ticker, "005930")
        self.assertEqual(profile.market, MarketType.KRX)
        self.assertEqual(profile.currency, "KRW")
        self.assertIn(ActorType.FOREIGN, profile.actor_flows)
        self.assertIn(ActorType.INST_PENSION, profile.actor_flows)
        self.assertIn(ActorType.RETAIL, profile.actor_flows)
        
        foreign_flow = profile.actor_flows[ActorType.FOREIGN]
        self.assertGreater(foreign_flow.net_value_20d, 0)
        self.assertLess(foreign_flow.estimated_vwap_20d, profile.current_price)
        
        retail_flow = profile.actor_flows[ActorType.RETAIL]
        self.assertGreater(retail_flow.estimated_vwap_20d, profile.current_price)
        self.assertGreater(profile.smart_money_hand_off_ratio, 0.0)

    def test_us_equity_flow_and_dark_pool(self):
        profile = self.disaggregator.disaggregate_stock_flow(
            ticker="AVGO",
            name="Broadcom Inc.",
            current_price=168.0,
            daily_volume=4_500_000,
            daily_turnover=756_000_000,
            market=MarketType.US
        )
        self.assertEqual(profile.ticker, "AVGO")
        self.assertEqual(profile.market, MarketType.US)
        self.assertEqual(profile.currency, "USD")
        self.assertIn(ActorType.DARK_POOL, profile.actor_flows)
        
        profile = self.sr_engine.calculate_levels(profile)
        # Verify Dark Pool VWAP or Options Gamma Wall presence
        dp_levels = [s for s in profile.support_levels if s.level_type == SupportResistanceType.DARK_POOL_VWAP]
        self.assertEqual(len(dp_levels), 1)
        self.assertLessEqual(dp_levels[0].price, profile.current_price)

    def test_support_resistance_calculation(self):
        profile = self.disaggregator.disaggregate_stock_flow(
            ticker="000660",
            name="SK하이닉스",
            current_price=212000.0,
            daily_volume=3_000_000,
            daily_turnover=636_000_000_000
        )
        profile = self.sr_engine.calculate_levels(profile)
        
        self.assertGreater(len(profile.support_levels), 0)
        self.assertGreater(len(profile.resistance_levels), 0)
        
        for s in profile.support_levels:
            self.assertLessEqual(s.price, profile.current_price)
            
        for r in profile.resistance_levels:
            self.assertGreaterEqual(r.price, profile.current_price)
            
        liq_levels = [s for s in profile.support_levels if s.level_type == SupportResistanceType.MARGIN_LIQUIDATION_LINE]
        self.assertEqual(len(liq_levels), 1)
        self.assertGreater(liq_levels[0].strength_score, 9.0)

    def test_dynamic_new_candidate_ingestion(self):
        # Dynamically ingest an unlisted new ticker: VST (Vistra Corp)
        new_item = self.subagent.ingest_new_candidate_stock(
            ticker="VST_NEW",
            name="Vistra Energy New Discovery",
            market=MarketType.US,
            sector="Nuclear/Power IPP",
            current_price=118.5,
            currency="USD",
            discovery_reason="텍사스 ERCOT 데이터센터 전력 급증 및 PPA 체결"
        )
        self.assertEqual(new_item.ticker, "VST_NEW")
        self.assertTrue(new_item.is_new_candidate)
        
        # Analyze the new stock
        analysis = self.subagent.analyze_stock(
            ticker=new_item.ticker,
            name=new_item.name,
            current_price=new_item.current_price,
            market=new_item.market,
            currency=new_item.currency,
            is_new_candidate=True
        )
        self.assertEqual(analysis["ticker"], "VST_NEW")
        self.assertGreater(analysis["forecast"].expected_return_5d_pct, 0.0)
        self.assertIn(analysis["trade_decision"].action, ["BUY", "STRONG_BUY", "HOLD"])

    def test_market_filtering_and_discovery_count(self):
        # 1. Market Filter = US
        us_results = self.subagent.run_subagent_pipeline(market_filter="us")
        for r in us_results["results"]:
            self.assertEqual(r["market"], MarketType.US)
            self.assertEqual(r["currency"], "USD")
            
        # 2. Market Filter = KR
        kr_results = self.subagent.run_subagent_pipeline(market_filter="kr")
        for r in kr_results["results"]:
            self.assertEqual(r["market"], MarketType.KRX)
            self.assertEqual(r["currency"], "KRW")
            
        # 3. Market Filter = ALL
        all_results = self.subagent.run_subagent_pipeline(market_filter="all")
        self.assertGreaterEqual(all_results["analyzed_count"], 10)
        self.assertGreaterEqual(all_results["newly_discovered_count"], 5)

    def test_subagent_full_pipeline_and_parent_integration(self):
        runner = InvestorAgentRunner()
        parent_flow_results = runner.run_order_flow_trading_pipeline(market_filter="all")
        
        self.assertGreaterEqual(parent_flow_results["analyzed_count"], 10)
        self.assertIn("subagent_memo", parent_flow_results)
        self.assertIn("MICRO_LUNR", runner.knowledge_graph.nodes)
        self.assertIn("MICRO_141080", runner.knowledge_graph.nodes)



    def test_ten_dollar_inflection_engine(self):
        # Test LUNR inflection scorecard
        lunr_card = self.subagent.inflection_engine.evaluate_candidate_inflection(
            ticker="LUNR",
            name="Intuitive Machines",
            current_price=5.20,
            market=MarketType.US,
            sector="Lunar Logistics / NSN",
            currency="USD"
        )
        self.assertEqual(lunr_card.ticker, "LUNR")
        self.assertGreaterEqual(lunr_card.total_inflection_score, 80.0)
        self.assertTrue(lunr_card.is_high_conviction_inflection_candidate)
        self.assertIn("4x ~ 8x", lunr_card.target_upside_multiplier)

        # Check historical case studies
        historic = self.subagent.inflection_engine.historic_benchmarks
        self.assertIn("PLTR", historic)
        self.assertIn("TSLA", historic)
        self.assertIn("RKLB", historic)
        self.assertIn("ASTS", historic)
        self.assertIn("IREN", historic)


if __name__ == "__main__":
    unittest.main()

