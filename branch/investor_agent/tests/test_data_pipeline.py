"""
Unit tests for Dynamic Data Pipeline & Timeline Ingestion.
"""
import unittest
from pathlib import Path
import tempfile
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.data_pipeline.dynamic_data_updater import DynamicDataUpdater
from src.data_pipeline.timeline_schema import TimelineDataSnapshot


class TestDynamicDataPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.updater = DynamicDataUpdater(data_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_snapshot_creation(self):
        snapshot = self.updater.get_latest_snapshot()
        self.assertIsInstance(snapshot, TimelineDataSnapshot)
        self.assertEqual(snapshot.macro.us_10y_yield_pct, 5.136)
        self.assertTrue(snapshot.policy.us_ira_45u_nuclear_ptc_active)

    def test_refresh_timeline_data_with_override(self):
        override = {
            "macro": {"us_10y_yield_pct": 3.85, "global_m2_yoy_pct": 8.1},
            "energy_commodities": {"copper_spot_usd_lb": 5.10},
            "policy": {"kr_value_up_tax_incentive_active": True}
        }
        updated = self.updater.refresh_timeline_data(override_metrics=override)
        self.assertEqual(updated.macro.us_10y_yield_pct, 3.85)
        self.assertEqual(updated.macro.global_m2_yoy_pct, 8.1)
        self.assertEqual(updated.energy_commodities.copper_spot_usd_lb, 5.10)
        self.assertEqual(updated.dynamic_feed_status, "LIVE_SYNCED_COMPREHENSIVE")


if __name__ == "__main__":
    unittest.main()
