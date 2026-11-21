"""
Portfolio Tracker: Monitors actual vs target weights, tracks portfolio drift, and generates rebalance orders.
"""
from typing import Dict, List, Any


class PortfolioTracker:
    def __init__(self, target_weights: Dict[str, float], cash_balance: float = 100000.0):
        self.target_weights = target_weights
        self.cash_balance = cash_balance
        self.current_positions: Dict[str, float] = {}  # asset_id -> market_value

    def update_positions(self, positions: Dict[str, float]):
        self.current_positions = positions

    def calculate_drift(self) -> List[Dict[str, Any]]:
        total_val = sum(self.current_positions.values()) + self.cash_balance
        if total_val == 0:
            return []

        drift_report = []
        for asset_id, target_w in self.target_weights.items():
            current_mkt_val = self.current_positions.get(asset_id, 0.0)
            current_w = current_mkt_val / total_val
            diff_w = target_w - current_w
            drift_report.append({
                "asset_id": asset_id,
                "target_weight_pct": target_w * 100.0,
                "current_weight_pct": current_w * 100.0,
                "drift_pct": diff_w * 100.0,
                "rebalance_action": "BUY" if diff_w > 0.02 else ("SELL" if diff_w < -0.02 else "HOLD")
            })
        return drift_report
