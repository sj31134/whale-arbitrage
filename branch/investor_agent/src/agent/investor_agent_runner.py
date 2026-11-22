"""
Investor Subagent Pipeline Orchestrator:
Executes pre-analysis data ingestion, research, scoring, valuation, barbell optimization,
memo generation, and automated memory/knowledge graph synchronization.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..research.macro_analyzer import MacroAnalyzer

from ..research.multi_asset_screener import MultiAssetScreener
from ..research.us_equity_screener import USEquityScreener
from ..research.kr_equity_screener import KREquityScreener
from ..research.jp_equity_screener import JPEquityScreener
from ..research.cn_equity_screener import CNEquityScreener
from ..research.global_macro_flow_analyzer import GlobalMacroFlowAnalyzer
from ..research.crypto_screener import CryptoScreener
from ..research.real_estate_screener import RealEstateScreener
from ..data_pipeline.dynamic_data_updater import DynamicDataUpdater
from ..strategy.scenario_modeler import ScenarioModeler
from ..strategy.barbell_optimizer import BarbellOptimizer
from ..strategy.risk_manager import RiskManager
from ..execution.investment_memo import InvestmentMemoGenerator
from ..memory.memory_manager import InvestmentMemoryManager
from ..graph.knowledge_graph import InvestmentKnowledgeGraph
from ..skills_distiller.skill_synthesizer import SkillSynthesizer
from ..subagents.order_flow import OrderFlowSubagent
from ..subagents.real_estate import RealEstateSubagent



class InvestorAgentRunner:
    def __init__(self, data_dir: Optional[Path] = None):
        base_data = Path(data_dir) if data_dir is not None else None
        self.data_updater = DynamicDataUpdater(data_dir=(base_data / "timeline") if base_data else None)
        self.macro_analyzer = MacroAnalyzer()
        self.screener = MultiAssetScreener()
        self.us_screener = USEquityScreener()
        self.kr_screener = KREquityScreener()
        self.jp_screener = JPEquityScreener()
        self.cn_screener = CNEquityScreener()
        self.macro_flow_analyzer = GlobalMacroFlowAnalyzer()
        self.crypto_screener = CryptoScreener()
        self.real_estate_screener = RealEstateScreener()
        self.scenario_modeler = ScenarioModeler(hurdle_rate=0.12, min_payoff_ratio=3.0)
        self.barbell_optimizer = BarbellOptimizer(core_target_weight=0.65, satellite_target_weight=0.35, cash_buffer=0.05)
        self.risk_manager = RiskManager(max_portfolio_drawdown=0.20)
        self.memo_generator = InvestmentMemoGenerator()
        self.memory = InvestmentMemoryManager(memory_dir=str(base_data / "memory") if base_data else None)
        self.knowledge_graph = InvestmentKnowledgeGraph(
            graph_path=str(base_data / "graph" / "knowledge_graph.json") if base_data else None
        )
        self.skill_synthesizer = SkillSynthesizer()
        self.order_flow_subagent = OrderFlowSubagent(
            hurdle_payoff=3.0,
            data_dir=(base_data / "order_flow") if base_data else None
        )
        self.real_estate_subagent = RealEstateSubagent(data_dir=base_data)


    def run_full_investment_pipeline(self) -> Dict[str, Any]:
        """
        Executes end-to-end investment research, scoring, valuation, barbell optimization,
        and committee memo generation with automated memory and knowledge graph synchronization.
        """
        # [Step 0] Pre-analysis Dynamic Data Ingestion
        timeline_snapshot = self.data_updater.refresh_timeline_data()

        # [Step 1] Macro Regime & Structural Tailwinds
        macro_summary = self.macro_analyzer.get_macro_summary()

        # [Step 2] Screen & Score Assets
        assets = self.screener.get_curated_universe()
        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        # [Step 3] Barbell Portfolio Allocation
        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        # [Step 4] Risk Management & Stress Testing
        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        # [Step 5] Institutional Memo Generation
        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        # [Step 6] Sync to Persistent Memory and Knowledge Graph
        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_us_equity_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused specifically on US Equities.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_summary = self.macro_analyzer.get_macro_summary()
        assets = self.us_screener.get_us_equity_universe()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_kr_equity_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused specifically on Korean Equities.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_summary = self.macro_analyzer.get_macro_summary()
        assets = self.kr_screener.get_kr_equity_universe()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_jp_equity_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused specifically on Japanese Equities.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_summary = self.macro_analyzer.get_macro_summary()
        assets = self.jp_screener.get_jp_equity_universe()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_cn_equity_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused specifically on Chinese Equities.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_summary = self.macro_analyzer.get_macro_summary()
        assets = self.cn_screener.get_cn_equity_universe()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_global_macro_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused on Global Macro Money Flows, Commodities & Logistics.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_framework = self.macro_flow_analyzer.get_global_macro_framework_summary()
        assets = self.macro_flow_analyzer.get_global_macro_assets()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": self.macro_analyzer.get_macro_summary(),
            "macro_framework": macro_framework,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_crypto_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused specifically on Crypto, Layer 1s, and RWA.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_summary = self.macro_analyzer.get_macro_summary()
        assets = self.crypto_screener.get_crypto_universe()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def run_real_estate_pipeline(self) -> Dict[str, Any]:
        """
        Executes institutional analysis focused on Prime Real Estate & Hard Physical Land Assets.
        """
        timeline_snapshot = self.data_updater.refresh_timeline_data()
        macro_summary = self.macro_analyzer.get_macro_summary()
        assets = self.real_estate_screener.get_real_estate_universe()

        scenario_evals = [self.scenario_modeler.evaluate_asset_scenarios(a) for a in assets]
        qualified_assets = [a for a in assets if a.is_investable]

        portfolio_results = self.barbell_optimizer.optimize_allocation(qualified_assets)

        asset_map = {a.id: a for a in assets}
        stress_test = self.risk_manager.stress_test_portfolio_bear_case(
            portfolio_results["allocated_assets"],
            asset_map
        )

        asset_memos = {a.id: self.memo_generator.generate_asset_memo(a) for a in qualified_assets}
        portfolio_memo = self.memo_generator.generate_portfolio_memo(portfolio_results)

        self._sync_memory_and_graph(assets, asset_memos)

        return {
            "timeline_snapshot": timeline_snapshot.to_dict(),
            "macro_summary": macro_summary,
            "total_screened_assets": len(assets),
            "qualified_assets_count": len(qualified_assets),
            "all_assets": assets,
            "portfolio_allocation": portfolio_results,
            "bear_stress_test": stress_test,
            "portfolio_memo": portfolio_memo,
            "asset_memos": asset_memos
        }

    def _sync_memory_and_graph(self, assets: List[Any], asset_memos: Dict[str, str]):
        """
        Persists analysis snapshots to Memory and dynamically updates the Knowledge Graph.
        """
        for a in assets:
            memo = asset_memos.get(a.id, "")
            asset_dict = {
                "name": a.name,
                "asset_class": a.asset_class.value,
                "tier": a.tier.value,
                "current_price": a.current_price,
                "intrinsic_value_base": a.intrinsic_value_base,
                "expected_return": a.scenarios.expected_return,
                "payoff_ratio": a.scenarios.payoff_ratio,
                "composite_score": a.skill_scores.weighted_composite_score,
                "bottleneck_role": a.bottleneck_role
            }
            # 1. Save to Memory
            self.memory.save_analysis_snapshot(a.id, asset_dict, memo)

            # 2. Update Knowledge Graph
            self.knowledge_graph.add_node(
                node_id=f"ASSET_{a.id}",
                node_type="Asset",
                label=a.name,
                metadata={"class": a.asset_class.value, "tier": a.tier.value, "score": a.skill_scores.weighted_composite_score}
            )
            if a.bottleneck_role:
                b_id = f"BOTTLENECK_{a.id}"
                self.knowledge_graph.add_node(
                    node_id=b_id,
                    node_type="Bottleneck",
                    label=a.bottleneck_role
                )
                self.knowledge_graph.add_edge(
                    source=f"ASSET_{a.id}",
                    target=b_id,
                    relation="CONTROLS_BOTTLENECK",
                    weight=0.95
                )

        self.knowledge_graph.save_graph()

    def run_order_flow_trading_pipeline(
        self,
        market_filter: str = "all",
        include_new_candidates: bool = True,
        custom_universe: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes the subordinate Order Flow & Microstructure Trading Subagent pipeline:
        - Disaggregates participant order flows across Korean (KRX) and US equities.
        - Dynamically discovers and ingests new candidate stocks.
        - Computes exact support/resistance levels from participant VWAPs & trapped volumes.
        - Forecasts 1D/5D prices via Causal Impact Network.
        - Generates tactical execution signals adhering to Parent Investor Principles (Payoff >= 3.0x).
        - Synchronizes state to parent Knowledge Graph.
        """
        results = self.order_flow_subagent.run_subagent_pipeline(
            market_filter=market_filter,
            include_new_candidates=include_new_candidates,
            target_universe=custom_universe
        )
        self.order_flow_subagent.sync_to_knowledge_graph(self.knowledge_graph, results["results"])
        return results

    def run_real_estate_subagent_pipeline(self) -> Dict[str, Any]:
        """
        Executes the subordinate Real Estate & Court Auction Subagent pipeline:
        - 3-Gate Hard Veto Screening on Multi-Tier Land Universe
        - Land Share Value Decomposition Simulation (V(t) = Land(e^gt) + Bldg(0))
        - 7-Step Court Auction Rights Analysis on Live Case Studies
        - Synchronizes state to parent Knowledge Graph.
        """
        results = self.real_estate_subagent.run_subagent_pipeline()
        self.real_estate_subagent.sync_to_knowledge_graph(self.knowledge_graph, results)
        return results



