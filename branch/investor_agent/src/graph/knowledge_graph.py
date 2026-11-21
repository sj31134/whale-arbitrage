"""
Investment Knowledge Graph: Models causal relationships, supply-chain dependencies, bottleneck nodes, and spillover links.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class InvestmentKnowledgeGraph:
    def __init__(self, graph_path: Optional[str] = None):
        if graph_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.graph_path = base_dir / "data" / "graph" / "knowledge_graph.json"
        else:
            self.graph_path = Path(graph_path)
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._load_graph()

    def _load_graph(self):
        if self.graph_path.exists():
            try:
                with open(self.graph_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
            except Exception:
                self._seed_default_graph()
        else:
            self._seed_default_graph()

    def _seed_default_graph(self):
        """
        Seeds baseline high-conviction graph relationships discovered in previous analyses.
        """
        self.nodes = {
            "MEGATREND_AI_COMPUTE": {"type": "Megatrend", "label": "AI Compute Scaling & Data Centers"},
            "MEGATREND_POWER_DEFICIT": {"type": "Megatrend", "label": "Zero-Carbon 24/7 Grid Power Deficit"},
            "MEGATREND_MONETARY_DEBASING": {"type": "Megatrend", "label": "Global Fiat Debt & Inflation"},
            
            # Real Estate
            "RE_HANNAM_UN": {"type": "Asset", "label": "Hannam UN Village Prime Land", "class": "Real Estate", "tier": "Core"},
            "LOC_SEOUL_HAN_RIVER": {"type": "Geography", "label": "Central Seoul South-Facing Han Riverfront"},
            "COHORT_UHNWI": {"type": "BuyerCohort", "label": "Top 0.01% Cash-Rich UHNWI"},

            # Equities / Bottlenecks
            "EQ_MSFT": {"type": "Asset", "label": "Microsoft Corporation", "class": "Equities", "tier": "Core"},
            "EQ_AVGO": {"type": "Asset", "label": "Broadcom Inc.", "class": "Equities", "tier": "Satellite"},
            "EQ_CEG": {"type": "Asset", "label": "Constellation Energy", "class": "Equities", "tier": "Satellite"},
            "EQ_TSMC": {"type": "Asset", "label": "TSMC Advanced Foundry", "class": "Equities", "tier": "Satellite"},
            "TECH_COWOS_PACKAGING": {"type": "Bottleneck", "label": "Advanced 2.5D/3D Chiplet Packaging (CoWoS)"},
            "TECH_OPTICAL_NETWORKING": {"type": "Bottleneck", "label": "High-Speed AI Cluster Switching (Tomahawk/SerDes)"},
            "TECH_NUCLEAR_BASELOAD": {"type": "Bottleneck", "label": "24/7 Zero-Carbon Nuclear Baseload Power"},

            # Hard Assets
            "CMD_GOLD": {"type": "Asset", "label": "Physical Allocated Gold", "class": "Commodities", "tier": "Core"},
            "CRYPTO_BTC": {"type": "Asset", "label": "Bitcoin Network", "class": "Crypto", "tier": "Satellite"}
        }

        self.edges = [
            # Real Estate Moats
            {"source": "RE_HANNAM_UN", "target": "LOC_SEOUL_HAN_RIVER", "relation": "PHYSIO_MONOPOLY_IN", "weight": 1.0},
            {"source": "COHORT_UHNWI", "target": "RE_HANNAM_UN", "relation": "PRICE_INELASTIC_DEMAND_FOR", "weight": 0.95},

            # Tech Bottlenecks & Relationships
            {"source": "MEGATREND_AI_COMPUTE", "target": "TECH_COWOS_PACKAGING", "relation": "ABSOLUTE_BOTTLENECK", "weight": 0.98},
            {"source": "MEGATREND_AI_COMPUTE", "target": "TECH_OPTICAL_NETWORKING", "relation": "ABSOLUTE_BOTTLENECK", "weight": 0.95},
            {"source": "MEGATREND_AI_COMPUTE", "target": "MEGATREND_POWER_DEFICIT", "relation": "CAUSES_SHORTAGE_OF", "weight": 0.99},
            
            {"source": "EQ_TSMC", "target": "TECH_COWOS_PACKAGING", "relation": "MONOPOLY_PROVIDER_OF", "weight": 0.95},
            {"source": "EQ_AVGO", "target": "TECH_OPTICAL_NETWORKING", "relation": "MONOPOLY_PROVIDER_OF", "weight": 0.90},
            {"source": "EQ_CEG", "target": "TECH_NUCLEAR_BASELOAD", "relation": "LARGEST_US_OPERATOR_OF", "weight": 0.98},

            # Corporate Interconnections
            {"source": "EQ_MSFT", "target": "EQ_CEG", "relation": "20YR_PPA_BUYER_FROM", "weight": 1.0},
            {"source": "EQ_MSFT", "target": "EQ_AVGO", "relation": "CUSTOM_ASIC_CUSTOMER_OF", "weight": 0.85},
            {"source": "EQ_MSFT", "target": "EQ_TSMC", "relation": "MAIA_CHIP_FABRICATED_BY", "weight": 0.90},

            # Macro Hard Assets
            {"source": "MEGATREND_MONETARY_DEBASING", "target": "CMD_GOLD", "relation": "DIRECT_VALUE_EXPANSION_TO", "weight": 0.95},
            {"source": "MEGATREND_MONETARY_DEBASING", "target": "CRYPTO_BTC", "relation": "MONETARY_SPILLOVER_TO", "weight": 0.90}
        ]
        self.save_graph()

    def add_node(self, node_id: str, node_type: str, label: str, metadata: Optional[Dict[str, Any]] = None):
        self.nodes[node_id] = {
            "type": node_type,
            "label": label,
            **(metadata or {})
        }
        self.save_graph()

    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0, metadata: Optional[Dict[str, Any]] = None):
        # Prevent duplicate identical edges
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation:
                edge["weight"] = weight
                return
        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
            **(metadata or {})
        })
        self.save_graph()

    def get_related_entities(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Finds all immediate connections (upstream, downstream, bottlenecks) for an entity.
        """
        connected = []
        for edge in self.edges:
            if edge["source"] == entity_id:
                target_node = self.nodes.get(edge["target"], {})
                connected.append({
                    "direction": "OUTGOING",
                    "relation": edge["relation"],
                    "node_id": edge["target"],
                    "node_label": target_node.get("label", edge["target"]),
                    "node_type": target_node.get("type", "Unknown")
                })
            elif edge["target"] == entity_id:
                source_node = self.nodes.get(edge["source"], {})
                connected.append({
                    "direction": "INCOMING",
                    "relation": edge["relation"],
                    "node_id": edge["source"],
                    "node_label": source_node.get("label", edge["source"]),
                    "node_type": source_node.get("type", "Unknown")
                })
        return connected

    def generate_mermaid_subgraph(self, focus_entity_id: Optional[str] = None) -> str:
        """
        Generates Mermaid diagram code representing the graph or a focal neighborhood.
        """
        lines = ["```mermaid", "graph TD"]
        
        # Add nodes
        for nid, data in self.nodes.items():
            safe_label = data.get("label", nid).replace('"', "'")
            ntype = data.get("type", "Node")
            if ntype == "Asset":
                lines.append(f'    {nid}["🏛️ {safe_label}"]')
            elif ntype == "Bottleneck":
                lines.append(f'    {nid}["⚡ BOTTLENECK: {safe_label}"]')
            elif ntype == "Megatrend":
                lines.append(f'    {nid}["🌊 TREND: {safe_label}"]')
            else:
                lines.append(f'    {nid}["{safe_label}"]')

        # Add edges
        for edge in self.edges:
            rel = edge["relation"].replace("_", " ")
            lines.append(f'    {edge["source"]} -->|"{rel}"| {edge["target"]}')

        lines.append("```")
        return "\n".join(lines)

    def save_graph(self):
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump({
                "nodes": self.nodes,
                "edges": self.edges,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
