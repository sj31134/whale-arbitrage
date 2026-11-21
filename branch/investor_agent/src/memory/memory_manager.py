"""
Memory Manager: Persistent storage and semantic retrieval for past investment theses, memos, and performance.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class InvestmentMemoryManager:
    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.memory_dir = base_dir / "data" / "memory"
        else:
            self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.memory_dir / "memory_index.json"
        self._init_index()

    def _init_index(self):
        if not self.index_file.exists():
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({"records": [], "last_updated": datetime.now().isoformat()}, f, indent=2)

    def save_analysis_snapshot(self, asset_id: str, asset_data: Dict[str, Any], memo_text: str):
        """
        Saves a structured snapshot and memo text into persistent memory.
        """
        timestamp = datetime.now().isoformat()
        record_id = f"{asset_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        record = {
            "record_id": record_id,
            "asset_id": asset_id,
            "asset_name": asset_data.get("name", ""),
            "asset_class": asset_data.get("asset_class", ""),
            "tier": asset_data.get("tier", ""),
            "current_price": asset_data.get("current_price", 0.0),
            "intrinsic_value": asset_data.get("intrinsic_value_base", 0.0),
            "expected_return": asset_data.get("expected_return", 0.0),
            "payoff_ratio": asset_data.get("payoff_ratio", 0.0),
            "composite_score": asset_data.get("composite_score", 0.0),
            "bottleneck_role": asset_data.get("bottleneck_role", ""),
            "timestamp": timestamp,
            "memo_path": str(self.memory_dir / f"{record_id}.md")
        }

        # Save Markdown memo
        with open(record["memo_path"], "w", encoding="utf-8") as f:
            f.write(memo_text)

        # Update index
        with open(self.index_file, "r+", encoding="utf-8") as f:
            data = json.load(f)
            # Remove older snapshot with same asset_id if we only want latest in fast index
            data["records"] = [r for r in data["records"] if r["asset_id"] != asset_id]
            data["records"].append(record)
            data["last_updated"] = timestamp
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)

    def retrieve_past_analysis(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest recorded memory for a given asset ID.
        """
        with open(self.index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for rec in data["records"]:
                if rec["asset_id"] == asset_id:
                    if Path(rec["memo_path"]).exists():
                        with open(rec["memo_path"], "r", encoding="utf-8") as mf:
                            rec["memo_content"] = mf.read()
                    return rec
        return None

    def search_memory(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple keyword-based memory retrieval across past investment theses.
        """
        query_lower = query.lower()
        results = []
        with open(self.index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for rec in data["records"]:
                if (
                    query_lower in rec["asset_id"].lower() or
                    query_lower in rec["asset_name"].lower() or
                    query_lower in rec["bottleneck_role"].lower() or
                    query_lower in rec["asset_class"].lower()
                ):
                    results.append(rec)
        return results
