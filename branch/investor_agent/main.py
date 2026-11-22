#!/usr/bin/env python3
"""
Investor Subagent: CLI and Orchestration Entry Point.
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.agent.investor_agent_runner import InvestorAgentRunner


def asset_memo_path(export_dir: Path, asset_id: str) -> Path:
    """Keep flat CLI exports while storing default asset memos with their owner."""
    export_path = export_dir / f"MEMO_{asset_id}.md"
    if export_dir.resolve() != BASE_DIR / "data" / "memos":
        return export_path

    prefix = asset_id.partition("-")[0]
    if prefix in {"US", "KR", "JP", "CN", "EQ"}:
        owner = "equities"
    elif prefix == "RE":
        owner = "real_estate"
    elif prefix == "CRYPTO":
        owner = "crypto"
    else:
        return export_path

    if not os.path.lexists(export_path):
        destination = BASE_DIR.parents[1] / "agents" / owner / "memos" / export_path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            export_path.symlink_to(os.path.relpath(destination, export_dir))
        except FileExistsError:
            pass  # Another export has already established the flat path.
    return export_path


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Multi-Asset Investor Subagent & Capital Allocation Engine"
    )
    parser.add_argument(
        "--universe",
        type=str,
        choices=["multi", "us_equities", "kr_equities", "jp_equities", "cn_equities", "global_macro", "crypto", "real_estate", "order_flow"],
        default="multi",
        help="Select investment asset universe to analyze (multi, us_equities, kr_equities, jp_equities, cn_equities, global_macro, crypto, real_estate, or order_flow)."
    )
    parser.add_argument(
        "--market",
        type=str,
        choices=["all", "kr", "us", "binance", "binance_tokenized"],
        default="all",
        help="Select market filter for order flow subagent: 'all', 'kr', 'us', or 'binance' (Binance 24/7 Tokenized Stocks)."
    )

    parser.add_argument(
        "--no-new",
        action="store_true",
        help="Exclude newly discovered breakout candidate stocks from analysis."
    )
    parser.add_argument(
        "--export-memos",
        type=str,
        default=str(BASE_DIR / "data" / "memos"),
        help="Directory to save generated investment committee markdown memos."
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print(f" 🚀 LAUNCHING INVESTOR SUBAGENT | UNIVERSE: {args.universe.upper()} (MARKET: {args.market.upper()})")
    print("=" * 80)

    runner = InvestorAgentRunner()
    if args.universe == "order_flow":
        flow_results = runner.run_order_flow_trading_pipeline(
            market_filter=args.market,
            include_new_candidates=not args.no_new
        )
        print(flow_results["subagent_memo"])
        print("\n" + "=" * 80)
        print(flow_results["risk_audit"]["audit_memo"])
        print("=" * 80)

        if args.export_memos:
            export_dir = Path(args.export_memos)
            export_dir.mkdir(parents=True, exist_ok=True)
            flow_memo_path = export_dir / "ORDER_FLOW_TRADING_MEMO.md"
            with open(flow_memo_path, "w", encoding="utf-8") as f:
                f.write(flow_results["subagent_memo"])
            risk_memo_path = export_dir / "THIRD_PARTY_RISK_AUDIT.md"
            with open(risk_memo_path, "w", encoding="utf-8") as f:
                f.write(flow_results["risk_audit"]["audit_memo"])
            print(f"\n[+] Subagent Order Flow Memo saved to: {flow_memo_path}")
            print(f"[+] Independent 3rd-Party Risk Audit saved to: {risk_memo_path}")
        print("\n" + "=" * 80)
        print(" ✅ ORDER FLOW SUBAGENT & 3RD-PARTY RISK AUDIT COMPLETE")
        print("=" * 80 + "\n")
        return



    if args.universe == "crypto":
        results = runner.run_crypto_pipeline()
    elif args.universe == "real_estate":
        results = runner.run_real_estate_pipeline()
    elif args.universe == "global_macro":
        results = runner.run_global_macro_pipeline()
    elif args.universe == "cn_equities":
        results = runner.run_cn_equity_pipeline()
    elif args.universe == "jp_equities":
        results = runner.run_jp_equity_pipeline()
    elif args.universe == "kr_equities":
        results = runner.run_kr_equity_pipeline()
    elif args.universe == "us_equities":
        results = runner.run_us_equity_pipeline()
    else:
        results = runner.run_full_investment_pipeline()


    print("\n[1] MACRO REGIME & STRUCTURAL TAILWINDS:")
    for k, v in results["macro_summary"].items():
        print(f"  • {k}: {v}")

    print(f"\n[2] ASSET SCREENING & QUALIFICATION:")
    print(f"  • Total Screened Universe: {results['total_screened_assets']} assets")
    print(f"  • Qualified Investable Assets: {results['qualified_assets_count']} assets")

    alloc = results["portfolio_allocation"]
    print(f"\n[3] MASTER BARBELL PORTFOLIO ALLOCATION:")
    print(f"  • Target Expected Return E[R]: +{alloc['portfolio_expected_return_pct'] * 100:.2f}%")
    print(f"  • Core Bucket Allocation: {alloc['core_weight_total'] * 100:.1f}%")
    print(f"  • Satellite Bucket Allocation: {alloc['satellite_weight_total'] * 100:.1f}%")
    print(f"  • Cash Reserve Buffer: {alloc['cash_buffer_weight'] * 100:.1f}%")

    print("\n[4] ACTIVE PORTFOLIO HOLDINGS:")
    for item in alloc["allocated_assets"]:
        print(f"  - [{item['tier']:<9}] {item['asset_name']:<45} | Weight: {item['recommended_weight_pct']*100:>5.1f}% | E[R]: +{item['expected_return_pct']*100:>4.1f}% | Payoff: {item['payoff_ratio']:>4.1f}x")

    stress = results["bear_stress_test"]
    print(f"\n[5] SYNCHRONIZED BEAR CASE STRESS TEST:")
    print(f"  • Portfolio Bear Return: {stress['portfolio_bear_scenario_return_pct'] * 100:.2f}%")
    print(f"  • Drawdown Limit Compliance (<= 20%): {'✅ PASSED' if stress['passes_max_drawdown_limit'] else '❌ FAILED'}")

    # Export Memos
    if args.export_memos:
        export_dir = Path(args.export_memos)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Save master portfolio memo
        portfolio_memo_path = export_dir / "MASTER_PORTFOLIO_ALLOCATION.md"
        with open(portfolio_memo_path, "w", encoding="utf-8") as f:
            f.write(results["portfolio_memo"])
            
        # Save individual memos
        for asset_id, memo_text in results["asset_memos"].items():
            memo_file = asset_memo_path(export_dir, asset_id)
            with open(memo_file, "w", encoding="utf-8") as f:
                f.write(memo_text)
                
        print(f"\n[6] INSTITUTIONAL INVESTMENT MEMOS GENERATED:")
        print(f"  • Master Report: {portfolio_memo_path}")
        print(f"  • Individual Memos Saved: {len(results['asset_memos'])} files in '{export_dir}'")

    print("\n" + "=" * 80)
    print(" ✅ EXECUTION COMPLETE - PORTFOLIO READY FOR ALLOCATION")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
