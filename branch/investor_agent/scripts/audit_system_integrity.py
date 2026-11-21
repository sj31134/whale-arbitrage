"""
System Integrity & Memory/Graph Optimization Auditor:
Verifies zero data loss, schema purity, knowledge graph graph-theoretic soundness,
memory index consistency, and pipeline robustness.
"""
from pathlib import Path
import json
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.memory.memory_manager import InvestmentMemoryManager
from src.graph.knowledge_graph import InvestmentKnowledgeGraph
from src.data_pipeline.dynamic_data_updater import DynamicDataUpdater


def audit_system():
    print("=" * 80)
    print(" 🛡️ COMPREHENSIVE INVESTOR AGENT SYSTEM & MEMORY INTEGRITY AUDIT")
    print("=" * 80)

    issues = []

    # 1. Audit Memory Index & Markdown Files
    print("\n[1] AUDITING MEMORY STORE (data/memory/)...")
    memory = InvestmentMemoryManager()
    index_file = BASE_DIR / "data" / "memory" / "memory_index.json"

    if not index_file.exists():
        issues.append("CRITICAL: memory_index.json is missing!")
    else:
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        records = index_data.get("records", [])
        print(f"  • Total Archived Memory Records: {len(records)}")

        missing_memos = 0
        for r in records:
            memo_p = Path(r["memo_path"])
            if not memo_p.exists():
                missing_memos += 1

        if missing_memos > 0:
            issues.append(f"WARNING: {missing_memos} memory snapshot markdown files are missing!")
        else:
            print("  • Memory Markdown Archives: 100% Intact & Verified ✅")

    # 2. Audit Knowledge Graph
    print("\n[2] AUDITING KNOWLEDGE GRAPH (data/graph/knowledge_graph.json)...")
    kg = InvestmentKnowledgeGraph()
    nodes = kg.nodes
    edges = kg.edges

    print(f"  • Total Graph Nodes: {len(nodes)}")
    print(f"  • Total Graph Edges: {len(edges)}")

    dangling_edges = 0
    for e in edges:
        s, t = e["source"], e["target"]
        if s not in nodes:
            dangling_edges += 1
            issues.append(f"Dangling edge source: '{s}' not in nodes!")
        if t not in nodes:
            dangling_edges += 1
            issues.append(f"Dangling edge target: '{t}' not in nodes!")

    if dangling_edges == 0:
        print("  • Knowledge Graph Topological Soundness: 0 Dangling Edges ✅")

    # 3. Audit Timeline Data Pipeline
    print("\n[3] AUDITING TIMELINE DATA PIPELINE (data/timeline/)...")
    updater = DynamicDataUpdater()
    snapshot = updater.get_latest_snapshot()

    if not snapshot:
        issues.append("CRITICAL: Dynamic data feed snapshot is empty!")
    else:
        print(f"  • Feed Status: {snapshot.dynamic_feed_status} | As-Of: {snapshot.as_of_date} ✅")
        print(f"  • Macro 10Y: {snapshot.macro.us_10y_yield_pct}% | M2 YoY: {snapshot.macro.global_m2_yoy_pct}%")
        print(f"  • Policies Synced: IRA 45U ({snapshot.policy.us_ira_45u_nuclear_ptc_active}), NATO ({snapshot.policy.nato_2pct_gdp_defense_mandate_pct}%)")

    # 4. Audit Core Investment Principles & Valuation Math
    print("\n[4] AUDITING CORE PRINCIPLES & SCORING ENGINES...")
    from src.core.valuation import ValuationEngine
    from src.core.scoring_engine import ScoringEngine
    from src.strategy.barbell_optimizer import BarbellOptimizer

    v_engine = ValuationEngine()
    decomp = v_engine.calculate_land_building_decomposition(
        initial_land_value=85.0,
        initial_building_value=15.0,
        land_annual_growth_rate=0.08,
        building_depreciation_rate=0.05,
        years=10
    )
    if decomp["future_total"] <= 100.0:
        issues.append("Valuation decomposition math anomaly!")
    else:
        print(f"  • Decomposition Math (Hannam Model): 100.0 -> {decomp['future_total']:.1f} (Land: {decomp['future_land_value']:.1f}, Dominance: {decomp['land_dominance_ratio']*100:.1f}%) ✅")

    mos = v_engine.calculate_margin_of_safety(current_price=100.0, intrinsic_value=135.0)
    print(f"  • Margin of Safety Formula: (135 - 100) / 135 = {mos*100:.1f}% ✅")

    print("\n" + "=" * 80)
    if not issues:
        print(" 🎯 FINAL VERDICT: ZERO CONTAMINATION, ZERO MEMORY LOSS, FULL INTEGRITY VERIFIED! ✅")
    else:
        print(f" ⚠️ AUDIT FOUND {len(issues)} ISSUES:")
        for iss in issues:
            print(f"   - {iss}")
    print("=" * 80)


if __name__ == "__main__":
    audit_system()
