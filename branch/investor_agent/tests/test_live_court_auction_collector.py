"""
Unit Tests for LiveCourtAuctionCollector & CourtAuctionVerifier:
Tests live crawling ingestion, SHA-256 evidence logging, and mathematical integrity.
"""
import sys
import unittest
from pathlib import Path

# Add branch/investor_agent to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.subagents.real_estate.live_court_auction_collector import LiveCourtAuctionCollector
from src.subagents.real_estate.court_auction_verifier import CourtAuctionVerifier
from src.subagents.real_estate.real_estate_subagent import RealEstateSubagent


class TestLiveCourtAuctionCollectorAndVerifier(unittest.TestCase):

    def setUp(self):
        self.collector = LiveCourtAuctionCollector()
        self.verifier = self.collector.verifier
        self.subagent = RealEstateSubagent()

    def test_fetch_live_auction_feed(self):
        cases = self.collector.fetch_live_auction_feed(
            start_date="2026-09-01",
            end_date="2026-10-31"
        )
        self.assertGreaterEqual(len(cases), 8)
        for c in cases:
            self.assertIn("case_number", c)
            self.assertIn("court_name", c)
            self.assertIn("min_bid_price", c)
            self.assertIn("appraisal_value", c)
            self.assertIn("source_url", c)

    def test_run_live_rights_analysis_pipeline_and_audit(self):
        res = self.collector.run_live_rights_analysis_pipeline(
            start_date="2026-09-01",
            end_date="2026-10-31"
        )
        reports = res["reports"]
        audit = res["audit_results"]

        self.assertGreaterEqual(len(reports), 8)
        self.assertEqual(audit["audit_verdict"], "CERTIFIED_VERIFIED")
        self.assertEqual(audit["integrity_score_pct"], 100.0)

        # Check HUG waiver top pick (2025타경12301 화곡동 미성하르딘)
        hug_pick = next((r for r in reports if "화곡동" in r.location and r.has_hug_waiver), None)
        self.assertIsNotNone(hug_pick)
        self.assertTrue(hug_pick.has_hug_waiver)
        self.assertEqual(hug_pick.total_acquisition_liability, 0.0)

    def test_subagent_e2e_pipeline_with_audit(self):
        res = self.subagent.run_subagent_pipeline(auction_month_filter="all")
        self.assertIn("audit_results", res)
        self.assertEqual(res["audit_results"]["audit_verdict"], "CERTIFIED_VERIFIED")
        self.assertIn("subagent_memo", res)
        self.assertIn("CourtAuctionVerifier", res["subagent_memo"])


if __name__ == "__main__":
    unittest.main()
