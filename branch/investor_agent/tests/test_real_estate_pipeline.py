"""
Unit Tests for RealEstateDataPipeline:
Tests multi-source ingestion (KB Real Estate, MOLIT, Urban Renewal, Court Auctions),
4-Pillar scoring, Cash 300M financial engineering, Anti-Price-Distortion Guardrails, and cache persistence.
"""
import sys
import tempfile
import unittest
from pathlib import Path

# Add branch/investor_agent to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.subagents.real_estate.real_estate_pipeline import RealEstateDataPipeline, MarketPropertyRecord
from src.subagents.real_estate.real_estate_subagent import RealEstateSubagent


class TestRealEstateDataPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.pipeline = RealEstateDataPipeline(data_dir=self.tmp_path / "real_estate")
        self.subagent = RealEstateSubagent(data_dir=self.tmp_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fetch_multi_source_listings(self):
        records = self.pipeline.fetch_multi_source_listings(
            min_price=350_000_000,
            max_price=850_000_000
        )
        self.assertGreaterEqual(len(records), 7)
        for r in records:
            self.assertIsInstance(r, MarketPropertyRecord)
            self.assertIsNotNone(r.raw_payload_hash)

    def test_price_sanity_audit_rejection(self):
        # A test hallucination: Bundang 59sqm for 6.8억
        passed, msg = self.pipeline.audit_price_sanity(
            region_cluster="판교IT배후(분당)",
            property_name="분당 서현 시범한양 59㎡",
            property_type="아파트",
            exclusive_area_sqm=59.3,
            price_total=680_000_000
        )
        self.assertFalse(passed)
        self.assertIn("CRITICAL_PRICE_ANOMALY", msg)

    def test_budget_exceeded_veto(self):
        records = self.pipeline.fetch_multi_source_listings()
        vetoed = [r for r in records if r.harness_verdict == "HARD_VETO_PRICE_EXCEEDED"]
        self.assertGreaterEqual(len(vetoed), 2)
        for v in vetoed:
            self.assertTrue(v.price_total > 850_000_000 or v.actual_cash_outflow_required > 300_000_000)

    def test_super_core_classification(self):
        records = self.pipeline.fetch_multi_source_listings()
        super_cores = [r for r in records if r.harness_verdict == "SUPER_CORE_PASS"]
        self.assertGreaterEqual(len(super_cores), 2)
        for sc in super_cores:
            self.assertGreaterEqual(sc.topography_inelasticity_score, 8.5)
            self.assertGreaterEqual(sc.land_dominance_ratio_pct, 65.0)
            self.assertLessEqual(sc.transit_time_minutes_to_hub, 20)
            self.assertLessEqual(sc.actual_cash_outflow_required, 300_000_000)

    def test_subagent_pipeline_integration(self):
        res = self.subagent.run_subagent_pipeline()
        self.assertIn("market_records", res)
        self.assertIn("super_core_market_records", res)
        self.assertGreaterEqual(len(res["market_records"]), 5)


if __name__ == "__main__":
    unittest.main()
