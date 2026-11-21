"""
Cross-Asset Knowledge Graph Sync: Maps the expanded global value chain,
semiconductor stack, critical energy/materials, and Seoul/Gyeonggi/Chungcheong real estate ladder.
"""
from pathlib import Path
import json
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.graph.knowledge_graph import InvestmentKnowledgeGraph


def sync_global_cross_asset_graph():
    kg = InvestmentKnowledgeGraph()

    # 1. Register All Expanded Regional Asset Nodes
    regional_assets = {
        # US & Global Monopolies
        "EQ_MSFT": {"label": "Microsoft (US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_AVGO": {"label": "Broadcom (US)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_CEG": {"label": "Constellation Energy (US)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_NVDA": {"label": "Nvidia (US)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_LLY": {"label": "Eli Lilly (US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_AMZN": {"label": "Amazon AWS (US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_COST": {"label": "Costco Wholesale (US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_ASML": {"label": "ASML Holding EUV (NL/US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_TSM": {"label": "TSMC Advanced Foundry (TW/US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_GOOGL": {"label": "Alphabet DeepMind/TPU (US)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_PLTR": {"label": "Palantir AIP OS (US)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_GE": {"label": "GE Aerospace Jet Engines (US)", "class": "Equities", "type": "Asset", "tier": "Core"},

        # Korea
        "EQ_SAMSUNG_ELEC": {"label": "Samsung Electronics (KR)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_SK_HYNIX": {"label": "SK hynix (KR)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_HD_HYUNDAI_ELEC": {"label": "HD Hyundai Electric (KR)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_MERITZ": {"label": "Meritz Financial (KR)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_SAM_BIO": {"label": "Samsung Biologics (KR)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_HYUNDAI_MOTOR": {"label": "Hyundai Motor (KR)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_ALTEOGEN": {"label": "Alteogen SC Bio (KR)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_APR": {"label": "APR Meditech (KR)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_DOOSAN_ENER": {"label": "Doosan Enerbility SMR (KR)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_HD_KSOE": {"label": "HD Korea Shipbuilding (KR)", "class": "Equities", "type": "Asset", "tier": "Satellite"},

        # Real Estate & Seoul/Gyeonggi/Chungcheong Land
        "RE_HANNAM_UN": {"label": "Hannam UN Village (Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_APGUJEONG": {"label": "Apgujeong Hyundai Land (Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_BANPO": {"label": "Banpo Trophy Land Share (Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_SEONGSU": {"label": "Seongsu Waterfront IT Land (Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_YEOUIDO": {"label": "Yeouido Financial Hub Land (Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_YONGSAN": {"label": "Yongsan Mega-Hub Land (Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_NOWON_RECON": {"label": "Nowon Sanggye Jugong (<10억 / Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_YONGSAN_VILLA": {"label": "Yongsan Wonhyo Villa (<10억 / Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_MAPO_YEOMRI": {"label": "Mapo Yeomri (<10억 / Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_SEONGDONG_SONGJEONG": {"label": "Seongdong Songjeong (<10억 / Seoul)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_BUNDANG_1ST": {"label": "Bundang 1st New Town (<10억 / Gyeonggi)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_PYEONGCHON_1ST": {"label": "Pyeongchon 1st New Town (<10억 / Gyeonggi)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_GWANGMYEONG_NT": {"label": "Gwangmyeong New Town (<10억 / Gyeonggi)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_SUWON_YEONGTONG": {"label": "Suwon Yeongtong (<10억 / Gyeonggi)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_ILSAN_1ST": {"label": "Ilsan 1st New Town (<10억 / Gyeonggi)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_CHEONAN_BULDANG": {"label": "Cheonan Buldang New Town (<10억 / Chungnam)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_DAEJEON_DUNSAN": {"label": "Daejeon Dunsan Croba (<10억 / Daejeon)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_CHEONGJU_OCHANG": {"label": "Cheongju Ochang Battery (<5억 / Chungbuk)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_SEJONG_SAETDEUM": {"label": "Sejong 2-2 Saetdeum (<10억 / Sejong)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_OSONG_BIO": {"label": "Chungbuk Osong Bio Square (<5억 / Chungbuk)", "class": "Real Estate", "type": "Asset", "tier": "Core"},
        "RE_DATACENTER_LAND": {"label": "Grid-Connected 500MW DC Land (US)", "class": "Real Estate", "type": "Asset", "tier": "Satellite"},

        # Japan
        "EQ_MITSUBISHI": {"label": "Mitsubishi Corp (JP)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_KEYENCE": {"label": "Keyence (JP)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_DISCO": {"label": "DISCO Corp (JP)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_TOKYO_ELEC": {"label": "Tokyo Electron (JP)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_LASERTEC": {"label": "Lasertec EUV (JP)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_SHIN_ETSU": {"label": "Shin-Etsu Chemical (JP)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_SONY": {"label": "Sony Group CIS (JP)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "ETF_JP_SEMI": {"label": "TIGER Japan Semi FactSet ETF (465660.KS)", "class": "Equities", "type": "Asset", "tier": "Satellite"},

        # China
        "EQ_MOUTAI": {"label": "Kweichow Moutai (CN)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_TENCENT": {"label": "Tencent Holdings (CN)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_NETEASE": {"label": "NetEase Games (CN)", "class": "Equities", "type": "Asset", "tier": "Core"},
        "EQ_MEITUAN": {"label": "Meituan Local Life (CN)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "EQ_XIAOMI": {"label": "Xiaomi HyperOS/EV (CN)", "class": "Equities", "type": "Asset", "tier": "Satellite"},
        "ETF_CN_SEMI": {"label": "TIGER China Semi FactSet ETF (396520.KS)", "class": "Equities", "type": "Asset", "tier": "Satellite"},

        # Commodities & Energy
        "CMD_BHP": {"label": "BHP Group (AU)", "class": "Commodities", "type": "Asset", "tier": "Core"},
        "CMD_CAMECO": {"label": "Cameco Uranium (CA)", "class": "Commodities", "type": "Asset", "tier": "Satellite"},
        "CMD_FCX": {"label": "Freeport Copper (US)", "class": "Commodities", "type": "Asset", "tier": "Satellite"},
        "CMD_LNG": {"label": "Cheniere Energy LNG (US)", "class": "Commodities", "type": "Asset", "tier": "Core"},
        "CMD_MP_MATERIALS": {"label": "MP Materials Rare Earths (US)", "class": "Commodities", "type": "Asset", "tier": "Satellite"},
        "CMD_NUTRIEN": {"label": "Nutrien Potash Fertilizer (CA)", "class": "Commodities", "type": "Asset", "tier": "Core"},
        "CMD_VALERO": {"label": "Valero Energy Refining (US)", "class": "Commodities", "type": "Asset", "tier": "Core"},
        "CMD_NEXTERA": {"label": "NextEra Energy Grid (US)", "class": "Commodities", "type": "Asset", "tier": "Core"},
        "CMD_SILVER": {"label": "Pan American Silver (US)", "class": "Commodities", "type": "Asset", "tier": "Satellite"},
        "CMD_GOLD": {"label": "Physical Gold (Global)", "class": "Commodities", "type": "Asset", "tier": "Core"},
        "CRYPTO_BTC": {"label": "Bitcoin (Digital Gold)", "class": "Crypto", "type": "Asset", "tier": "Satellite"},
    }

    for node_id, data in regional_assets.items():
        node_type = data.get("type", "Asset")
        label = data.get("label", node_id)
        meta = {k: v for k, v in data.items() if k not in ["type", "label"]}
        kg.add_node(node_id, node_type, label, meta)

    # 2. Add Causal Value-Chain Interconnections
    edges = [
        # ASML & TEL -> TSMC & Samsung
        ("EQ_ASML", "EQ_TSM", "EXCLUSIVELY_SUPPLIES_EUV", 1.0),
        ("EQ_TOKYO_ELEC", "EQ_TSM", "SUPPLIES_COATER_DEVELOPER", 0.95),
        ("EQ_LASERTEC", "EQ_TSM", "INSPECTS_EUV_MASKS", 1.0),
        ("EQ_SHIN_ETSU", "EQ_TSM", "SUPPLIES_SILICON_WAFERS", 0.98),
        ("EQ_TSM", "EQ_NVDA", "MANUFACTURES_BLACKWELL_GPU", 0.98),
        ("EQ_DISCO", "EQ_SK_HYNIX", "GRINDS_HBM_WAFERS", 0.95),
        ("EQ_SK_HYNIX", "EQ_NVDA", "SUPPLIES_HBM3E", 0.98),
        ("EQ_SAMSUNG_ELEC", "EQ_NVDA", "SUPPLIES_HBM4_DRAM", 0.95),
        ("EQ_NVDA", "EQ_MSFT", "POWERS_AZURE_AI", 0.95),

        # Power & Infrastructure Bottleneck
        ("CMD_CAMECO", "EQ_CEG", "FEEDS_NUCLEAR_REACTORS", 0.95),
        ("EQ_DOOSAN_ENER", "CMD_CAMECO", "MANUFACTURES_SMR_REACTORS", 0.90),
        ("CMD_FCX", "EQ_HD_HYUNDAI_ELEC", "SUPPLIES_COPPER_CONDUCTORS", 0.95),
        ("EQ_HD_HYUNDAI_ELEC", "EQ_MSFT", "PROVIDES_DATA_CENTER_TRANSFORMERS", 0.95),
        ("CMD_NEXTERA", "RE_DATACENTER_LAND", "SUPPLIES_GRID_POWER", 0.95),

        # Critical Materials
        ("CMD_MP_MATERIALS", "EQ_HYUNDAI_MOTOR", "SUPPLIES_RARE_EARTH_MAGNETS", 0.92),
        ("CMD_SILVER", "EQ_SAMSUNG_ELEC", "SUPPLIES_SEMICONDUCTOR_PASTE", 0.90),

        # Real Estate Wealth Transfer Ladder & Industrial Anchors
        ("EQ_SAMSUNG_ELEC", "RE_SUWON_YEONGTONG", "EMPLOYMENT_ANCHOR_FOR", 0.98),
        ("EQ_SAMSUNG_ELEC", "RE_CHEONAN_BULDANG", "EMPLOYMENT_ANCHOR_FOR", 0.95),
        ("EQ_SK_HYNIX", "RE_CHEONGJU_OCHANG", "M15X_FAB_PROXIMITY_TO", 0.92),
        ("RE_CHEONAN_BULDANG", "RE_BUNDANG_1ST", "CAPITAL_LADDER_UPGRADE", 0.90),
        ("RE_SUWON_YEONGTONG", "RE_YONGSAN", "CAPITAL_LADDER_UPGRADE", 0.92),
        ("RE_NOWON_RECON", "RE_YONGSAN", "CAPITAL_LADDER_UPGRADE", 0.90),
        ("RE_BUNDANG_1ST", "RE_APGUJEONG", "CAPITAL_LADDER_UPGRADE", 0.92),
        ("RE_YONGSAN_VILLA", "RE_HANNAM_UN", "CAPITAL_LADDER_UPGRADE", 0.95),
    ]

    for source, target, rel_type, weight in edges:
        kg.add_edge(source, target, rel_type, weight)

    kg.save_graph()
    print("✅ Master Expanded Global Cross-Asset Knowledge Graph Synced Successfully!")


if __name__ == "__main__":
    sync_global_cross_asset_graph()
