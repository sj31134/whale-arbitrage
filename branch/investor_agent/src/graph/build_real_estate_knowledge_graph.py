"""
Builds the Comprehensive Global-to-Local Real Estate Network Knowledge Graph:
Combines:
1. Hannam UN Village 5 Invariable Axioms (4-Pillar Harness)
2. Global 8 Megacity Upzoning Variables (X1 ~ X8)
3. Seoul & Metropolitan Regional Hubs
4. Real-world Verified Properties & Land Assets

Computes network edge connections, transmission paths, and node convergence centrality scores.
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


def build_real_estate_network_graph() -> Dict[str, Any]:
    base_dir = Path(__file__).resolve().parent.parent.parent
    graph_file = base_dir / "data" / "graph" / "real_estate_knowledge_graph.json"
    graph_file.parent.mkdir(parents=True, exist_ok=True)

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    # =========================================================================
    # 1. CORE THEORETICAL & HARNESS NODES (Hannam Axioms & Global Variables)
    # =========================================================================
    theory_nodes = {
        # --- Pillar 1: Asset Decomposition & Land Compounding ---
        "VAR_LAND_COMPOUNDING": {
            "type": "TheoreticalVariable",
            "category": "Pillar 1: Asset Decomposition",
            "label": "대지지분 복리 성장 공식 V(t) = Land(e^gt) + Bldg(0)",
            "description": "건물 감가상각 소멸 대비 토지지분 가치 비중 70%+ 및 복리 팽창",
            "weight": 1.0
        },
        # --- Pillar 2: Monopoly Moat & Upzoning ---
        "VAR_TOPOGRAPHY_INELASTICITY": {
            "type": "TheoreticalVariable",
            "category": "Pillar 2: Monopoly Moat",
            "label": "지형적 독점 & 공급 비탄력성 (Es ≈ 0)",
            "description": "물리적 평지 고갈, 강/산 폐쇄 지형, 신규 택지 확장 불가",
            "weight": 0.95
        },
        "VAR_DOOR_TO_DOOR_TRANSIT": {
            "type": "TheoreticalVariable",
            "category": "Pillar 2: Monopoly Moat",
            "label": "급행 30분 직주근접 병목 Corridor (500m 초역세권)",
            "description": "도보 5분 이내 급행/환승역 결절점",
            "weight": 0.90
        },
        # --- Pillar 3: Solvency Cohort ---
        "VAR_SOLVENCY_COHORT": {
            "type": "TheoreticalVariable",
            "category": "Pillar 3: High-Income Cohort",
            "label": "고소득 지불여력 코호트 독점 (C_solvency)",
            "description": "AI/IT, 반도체, 금융 등 평당 7천만~1억 분양가를 흡수하는 실수요층",
            "weight": 0.95
        },
        # --- Pillar 4: Legal Safety & Policy ---
        "VAR_LEGAL_SAFETY_MARGIN": {
            "type": "TheoreticalVariable",
            "category": "Pillar 4: Policy & Legal",
            "label": "권리분석 안전마진 & 도정법 제39조 조합원 승계 (α=1)",
            "description": "인수금 0원, HUG 대항력 포기 확약, 조합원 지위 양도 합법성",
            "weight": 0.98
        },

        # --- NEW GLOBAL MEGACITY 8 UPZONING VARIABLES (X1 ~ X8) ---
        "NODE_X1_TRANSIT_CONVERGENCE": {
            "type": "GlobalUpzoningVariable",
            "category": "Upzoning Catalyst",
            "label": "X1: 메가 환승 결절점 지수 (τ_transit ≥ 3개 노선)",
            "description": "지하철 3개 노선 이상, GTX/KTX 고속철도 환승 허브 500m 이내",
            "weight": 1.0
        },
        "NODE_X2_MEGA_ANCHOR_LAND": {
            "type": "GlobalUpzoningVariable",
            "category": "Upzoning Catalyst",
            "label": "X2: 인접 메가 앵커 대지 (Λ_anchor ≥ 1만 평)",
            "description": "1만 평 이상의 철도정비창, 차량기지, 터미널, 이전적지 인접",
            "weight": 1.0
        },
        "NODE_X3_SOLVENCY_ABSORPTION": {
            "type": "GlobalUpzoningVariable",
            "category": "Upzoning Catalyst",
            "label": "X3: 고소득 일반분양가 흡수력 (C_solv)",
            "description": "초고층 주거복합 평당 7,000만~1억 원 완판 지불여력",
            "weight": 0.90
        },
        "NODE_X4_PRE_FAR_GAP": {
            "type": "GlobalUpzoningVariable",
            "category": "Spatial Morphology",
            "label": "X4: 원시 용적률 갭 (Φ_pre_FAR ≤ 150%)",
            "description": "현재 용적률이 낮아 향후 800%~1,500% 상향 시 가치 폭발 갭 극대화",
            "weight": 0.95
        },
        "NODE_X5_OWNERSHIP_CONCENTRATION": {
            "type": "GlobalUpzoningVariable",
            "category": "Spatial Morphology",
            "label": "X5: 소유주 분산도 역수 (1 / Ω_frag)",
            "description": "지분 쪼개기 없는 원시 단독/다가구/대형필지 위주 대지 독점",
            "weight": 0.92
        },
        "NODE_X6_ROAD_FRONTAGE": {
            "type": "GlobalUpzoningVariable",
            "category": "Spatial Morphology",
            "label": "X6: 간선도로 접면폭 (ρ_road ≥ 20m)",
            "description": "초고층 방재 및 교통 인프라 수용이 가능한 4차선 이상 대로변",
            "weight": 0.88
        },
        "NODE_X7_SPECIAL_ZONE_ELIGIBILITY": {
            "type": "GlobalUpzoningVariable",
            "category": "Policy Incentive",
            "label": "X7: 공간혁신구역(화이트존) 부합도 (Ψ_zone)",
            "description": "2040 서울플랜 비욘드 조닝, 역세권 활성화, 준공업지 혁신 구역",
            "weight": 0.95
        },
        "NODE_X8_AIR_RIGHTS_BONUS": {
            "type": "GlobalUpzoningVariable",
            "category": "Policy Incentive",
            "label": "X8: 공공기여 교환 인센티브 승수 (κ_contrib)",
            "description": "기부채납 15~25% 대비 용적률 최대 3~4배 인센티브 환산",
            "weight": 0.90
        }
    }
    nodes.update(theory_nodes)

    # =========================================================================
    # 2. REGIONAL URBAN HUB NODES (Korea / Seoul Metropolitan Target Regions)
    # =========================================================================
    regional_nodes = {
        "REGION_YONGSAN_CORE": {
            "type": "UrbanRegionHub",
            "label": "용산 국제업무지구 배후권 (원효로1가·청파동·한강로)",
            "macro_hub": "용산 51조 메가특구",
            "existing_far_pct": 140,
            "target_far_pct": 1200,
            "transit_lines_count": 5,
            "anchor_land_pyeong": 150000,
            "convergence_score": 9.85
        },
        "REGION_YEONGDEUNGPO_MULLAE": {
            "type": "UrbanRegionHub",
            "label": "영등포 문래동 준공업지역 밸리 (문래4가·당산동·양평동)",
            "macro_hub": "여의도 YBD 배후 준공업 혁신",
            "existing_far_pct": 180,
            "target_far_pct": 500,
            "transit_lines_count": 3,
            "anchor_land_pyeong": 35000,
            "convergence_score": 9.42
        },
        "REGION_SEONGSU_SONGJEONG": {
            "type": "UrbanRegionHub",
            "label": "성수 준공업지 & 삼표 배후 (성수동2가·송정동·사근동)",
            "macro_hub": "성수 IT 밸리 & 삼표 글로벌 특구",
            "existing_far_pct": 150,
            "target_far_pct": 800,
            "transit_lines_count": 3,
            "anchor_land_pyeong": 28000,
            "convergence_score": 9.35
        },
        "REGION_CHEONGNYANGNI_JEGI": {
            "type": "UrbanRegionHub",
            "label": "청량리 쿼드러플 환승 허브 (제기동·용두동 역세권 350m)",
            "macro_hub": "동북권 최대 메가 환승 결절점",
            "existing_far_pct": 190,
            "target_far_pct": 1100,
            "transit_lines_count": 6,
            "anchor_land_pyeong": 22000,
            "convergence_score": 9.15
        },
        "REGION_GANGSEO_BANGHWA": {
            "type": "UrbanRegionHub",
            "label": "강서 방화뉴타운 권역 (5호선 방화/개화산역 역세권)",
            "macro_hub": "마곡 R&D 10만 직주 배후",
            "existing_far_pct": 160,
            "target_far_pct": 300,
            "transit_lines_count": 2,
            "anchor_land_pyeong": 15000,
            "convergence_score": 8.70
        },
        "REGION_PYEONGCHON_BEOMGYE": {
            "type": "UrbanRegionHub",
            "label": "안양 평촌 1기 신도시 권역 (4호선 범계역 / 평촌학원가)",
            "macro_hub": "평촌 학원가 & 선도지구 특별법",
            "existing_far_pct": 190,
            "target_far_pct": 380,
            "transit_lines_count": 2,
            "anchor_land_pyeong": 18000,
            "convergence_score": 8.65
        },
        "REGION_NOWON_CHANGDONG": {
            "type": "UrbanRegionHub",
            "label": "노원·창동 바이오밸리 권역 (4·7호선 노원역 / 창동역)",
            "macro_hub": "창동 차량기지 이전 & 바이오 특구",
            "existing_far_pct": 180,
            "target_far_pct": 400,
            "transit_lines_count": 3,
            "anchor_land_pyeong": 75000,
            "convergence_score": 8.55
        },
        # --- Value Trap Negative Controls ---
        "TRAP_PERIPHERY_YANGJU": {
            "type": "UrbanRegionTrap",
            "label": "수도권 외곽 그린필드 (양주 옥정 / 포천)",
            "macro_hub": "무한 확장 베드타운 (Es >> 1.0)",
            "existing_far_pct": 180,
            "target_far_pct": 200,
            "transit_lines_count": 1,
            "anchor_land_pyeong": 0,
            "convergence_score": 2.10
        },
        "TRAP_PERIPHERY_GIMPO": {
            "type": "UrbanRegionTrap",
            "label": "수도권 외곽 비역세 (김포 통진 / 대곶)",
            "macro_hub": "수요 부재 외곽 (Es >> 1.0)",
            "existing_far_pct": 120,
            "target_far_pct": 150,
            "transit_lines_count": 0,
            "anchor_land_pyeong": 0,
            "convergence_score": 1.85
        }
    }
    nodes.update(regional_nodes)

    # =========================================================================
    # 3. VERIFIED REAL ASSET NODES (Properties & Land Shares)
    # =========================================================================
    asset_nodes = {
        "ASSET_YONGSAN_WONHYO_VILLA": {
            "type": "VerifiedTargetAsset",
            "label": "용산 원효로1가 모아타운 1구역 다세대 201호",
            "region": "REGION_YONGSAN_CORE",
            "market_price": 580_000_000,
            "land_area_pyeong": 8.4,
            "land_dominance_ratio": 82.0,
            "existing_far": 135,
            "expected_upzoned_far": 950,
            "far_multiplier": 7.04,
            "network_rank": 1,
            "harness_verdict": "SUPER_UPZONING_CROWN"
        },
        "ASSET_MULLAE_4GA_LAND": {
            "type": "VerifiedTargetAsset",
            "label": "영등포 문래동4가 도시환경정비 지분 (대지 11.2평)",
            "region": "REGION_YEONGDEUNGPO_MULLAE",
            "market_price": 620_000_000,
            "land_area_pyeong": 11.2,
            "land_dominance_ratio": 85.0,
            "existing_far": 170,
            "expected_upzoned_far": 500,
            "far_multiplier": 2.94,
            "network_rank": 2,
            "harness_verdict": "SUPER_UPZONING_PASS"
        },
        "ASSET_SONGJEONG_MOATOWN_VILLA": {
            "type": "VerifiedTargetAsset",
            "label": "성동구 송정동 모아타운 다세대 102호 (대지 8.5평)",
            "region": "REGION_SEONGSU_SONGJEONG",
            "market_price": 480_000_000,
            "land_area_pyeong": 8.5,
            "land_dominance_ratio": 82.0,
            "existing_far": 145,
            "expected_upzoned_far": 450,
            "far_multiplier": 3.10,
            "network_rank": 3,
            "harness_verdict": "SUPER_UPZONING_PASS"
        },
        "ASSET_JEGI_STATION_LAND": {
            "type": "VerifiedTargetAsset",
            "label": "동대문구 제기동 역세권 활성화 정비 지분 (대지 7.8평)",
            "region": "REGION_CHEONGNYANGNI_JEGI",
            "market_price": 460_000_000,
            "land_area_pyeong": 7.8,
            "land_dominance_ratio": 78.0,
            "existing_far": 180,
            "expected_upzoned_far": 800,
            "far_multiplier": 4.44,
            "network_rank": 4,
            "harness_verdict": "PRIME_UPZONING_PASS"
        },
        "ASSET_BANGHWA_5DANJI_49": {
            "type": "VerifiedTargetAsset",
            "label": "서울 강서구 방화동 방화5단지 전용 49㎡ (20평형)",
            "region": "REGION_GANGSEO_BANGHWA",
            "market_price": 750_000_000,
            "land_area_pyeong": 12.0,
            "land_dominance_ratio": 80.0,
            "existing_far": 160,
            "expected_upzoned_far": 300,
            "far_multiplier": 1.88,
            "network_rank": 5,
            "harness_verdict": "PRIME_UPZONING_PASS"
        },
        "ASSET_PYEONGCHON_SAETBYEOL_48": {
            "type": "VerifiedTargetAsset",
            "label": "경기 안양 평촌 샛별한양 6단지 전용 48㎡ (20평형)",
            "region": "REGION_PYEONGCHON_BEOMGYE",
            "market_price": 550_000_000,
            "land_area_pyeong": 8.8,
            "land_dominance_ratio": 72.0,
            "existing_far": 190,
            "expected_upzoned_far": 380,
            "far_multiplier": 2.00,
            "network_rank": 6,
            "harness_verdict": "HYBRID_CORE_PASS"
        },
        "ASSET_HUG_HWA_GOK_501": {
            "type": "VerifiedTargetAsset",
            "label": "강서 화곡 미성하르딘 501호 (HUG 대항력포기 확약 경매)",
            "region": "REGION_GANGSEO_BANGHWA",
            "market_price": 124_920_000,
            "land_area_pyeong": 6.5,
            "land_dominance_ratio": 74.0,
            "existing_far": 190,
            "expected_upzoned_far": 250,
            "far_multiplier": 1.32,
            "network_rank": 7,
            "harness_verdict": "ASYMMETRIC_AUCTION_ALPHA"
        }
    }
    nodes.update(asset_nodes)

    # =========================================================================
    # 4. NETWORK EDGES: CAUSAL & TRANSMISSION LINKS
    # =========================================================================
    # Define transmission matrix from Theory/Global variables to Regions
    region_variable_links = [
        # Yongsan Core (Highest Convergence)
        ("REGION_YONGSAN_CORE", "VAR_LAND_COMPOUNDING", "TRANSMITS_COMPOUNDING", 1.0),
        ("REGION_YONGSAN_CORE", "VAR_TOPOGRAPHY_INELASTICITY", "PERFECT_HAN_RIVER_ISOLATION", 1.0),
        ("REGION_YONGSAN_CORE", "VAR_DOOR_TO_DOOR_TRANSIT", "GTX_B_KTX_QUAD_HUB", 0.98),
        ("REGION_YONGSAN_CORE", "VAR_SOLVENCY_COHORT", "GLOBAL_FINANCE_TECH_ABSORPTION", 1.0),
        ("REGION_YONGSAN_CORE", "NODE_X1_TRANSIT_CONVERGENCE", "CONNECTS_5_METRO_LINES", 1.0),
        ("REGION_YONGSAN_CORE", "NODE_X2_MEGA_ANCHOR_LAND", "ADJACENT_TO_150K_PYEONG_RAILYARDS", 1.0),
        ("REGION_YONGSAN_CORE", "NODE_X3_SOLVENCY_ABSORPTION", "ABSORBS_100M_PYEONG_PRICE", 1.0),
        ("REGION_YONGSAN_CORE", "NODE_X4_PRE_FAR_GAP", "MAX_GAP_140_TO_1200_PCT", 1.0),
        ("REGION_YONGSAN_CORE", "NODE_X5_OWNERSHIP_CONCENTRATION", "MOATOWN_COORDINATED_LAND", 0.92),
        ("REGION_YONGSAN_CORE", "NODE_X6_ROAD_FRONTAGE", "WONHYORO_40M_BOULEVARD", 0.95),
        ("REGION_YONGSAN_CORE", "NODE_X7_SPECIAL_ZONE_ELIGIBILITY", "DESIGNATED_WHITE_ZONE_LEAD", 1.0),
        ("REGION_YONGSAN_CORE", "NODE_X8_AIR_RIGHTS_BONUS", "MAX_FAR_1700_PCT_INCENTIVE", 1.0),

        # Yeongdeungpo Mullae
        ("REGION_YEONGDEUNGPO_MULLAE", "VAR_LAND_COMPOUNDING", "TRANSMITS_COMPOUNDING", 0.95),
        ("REGION_YEONGDEUNGPO_MULLAE", "VAR_SOLVENCY_COHORT", "YBD_FINANCIAL_COHORT", 0.95),
        ("REGION_YEONGDEUNGPO_MULLAE", "NODE_X1_TRANSIT_CONVERGENCE", "LINE_2_LINE_1_LINE_5", 0.90),
        ("REGION_YEONGDEUNGPO_MULLAE", "NODE_X2_MEGA_ANCHOR_LAND", "MULLAE_INDUSTRIAL_LARGE_PARCELS", 0.95),
        ("REGION_YEONGDEUNGPO_MULLAE", "NODE_X4_PRE_FAR_GAP", "GAP_180_TO_500_PCT", 0.95),
        ("REGION_YEONGDEUNGPO_MULLAE", "NODE_X7_SPECIAL_ZONE_ELIGIBILITY", "SEOUL_SEMI_INDUSTRIAL_ORDINANCE", 1.0),
        ("REGION_YEONGDEUNGPO_MULLAE", "NODE_X6_ROAD_FRONTAGE", "DANGSANRO_25M_ARTERIAL", 0.90),

        # Seongsu Songjeong
        ("REGION_SEONGSU_SONGJEONG", "VAR_TOPOGRAPHY_INELASTICITY", "JUNGRANG_STREAM_WATERFRONT", 0.95),
        ("REGION_SEONGSU_SONGJEONG", "VAR_SOLVENCY_COHORT", "SEONGSU_IT_UNICORN_COHORT", 1.0),
        ("REGION_SEONGSU_SONGJEONG", "NODE_X2_MEGA_ANCHOR_LAND", "SAMPYO_GLOBAL_BUSINESS_PARCEL", 1.0),
        ("REGION_SEONGSU_SONGJEONG", "NODE_X4_PRE_FAR_GAP", "GAP_150_TO_800_PCT", 0.95),
        ("REGION_SEONGSU_SONGJEONG", "NODE_X7_SPECIAL_ZONE_ELIGIBILITY", "MOATOWN_SEONGSU_SPILLOVER", 0.95),

        # Cheongnyangni Jegi
        ("REGION_CHEONGNYANGNI_JEGI", "NODE_X1_TRANSIT_CONVERGENCE", "GTX_B_GTX_C_KTX_6_LINES", 1.0),
        ("REGION_CHEONGNYANGNI_JEGI", "NODE_X7_SPECIAL_ZONE_ELIGIBILITY", "STATION_ACTIVATION_1100_PCT", 0.95),
        ("REGION_CHEONGNYANGNI_JEGI", "NODE_X6_ROAD_FRONTAGE", "WANGSANRO_35M_BOULEVARD", 0.95),

        # Gangseo Banghwa
        ("REGION_GANGSEO_BANGHWA", "VAR_SOLVENCY_COHORT", "MAGOK_RD_100K_COHORT", 0.95),
        ("REGION_GANGSEO_BANGHWA", "VAR_DOOR_TO_DOOR_TRANSIT", "LINE_5_BANGHWA_STATION", 0.90),
        ("REGION_GANGSEO_BANGHWA", "NODE_X4_PRE_FAR_GAP", "RECONSTRUCTION_160_TO_300_PCT", 0.88),

        # Pyeongchon Beomgye
        ("REGION_PYEONGCHON_BEOMGYE", "VAR_SOLVENCY_COHORT", "PYEONGCHON_ACADEMY_PARENTS", 0.92),
        ("REGION_PYEONGCHON_BEOMGYE", "NODE_X7_SPECIAL_ZONE_ELIGIBILITY", "SPECIAL_RECONSTRUCTION_ACT_LEAD", 0.95),

        # Traps (Inelasticity Failure)
        ("TRAP_PERIPHERY_YANGJU", "VAR_TOPOGRAPHY_INELASTICITY", "INFINITE_SUPPLY_FAILURE", -1.0),
        ("TRAP_PERIPHERY_GIMPO", "VAR_TOPOGRAPHY_INELASTICITY", "NO_DEMAND_FAR_TRAP", -1.0)
    ]

    for reg, var, rel, w in region_variable_links:
        edges.append({
            "source": reg,
            "target": var,
            "relationship": rel,
            "weight": w
        })

    # Assets to Region links
    for aid, adata in asset_nodes.items():
        edges.append({
            "source": aid,
            "target": adata["region"],
            "relationship": "LOCATED_IN_UPZONING_REGION",
            "weight": 1.0
        })
        edges.append({
            "source": aid,
            "target": "VAR_LAND_COMPOUNDING",
            "relationship": f"CARRIES_{adata['land_area_pyeong']}_PYEONG_LAND",
            "weight": adata["land_dominance_ratio"] / 100.0
        })

    # Compute Centrality & In-degree convergence metrics
    node_degrees: Dict[str, int] = {k: 0 for k in nodes}
    for e in edges:
        if e["source"] in node_degrees:
            node_degrees[e["source"]] += 1
        if e["target"] in node_degrees:
            node_degrees[e["target"]] += 1

    for nid in nodes:
        nodes[nid]["network_degree"] = node_degrees.get(nid, 0)

    # Top Common Characteristics among Converged Nodes
    top_converged_regions = sorted(
        [k for k, v in nodes.items() if v["type"] == "UrbanRegionHub"],
        key=lambda x: nodes[x].get("convergence_score", 0),
        reverse=True
    )

    graph_payload = {
        "metadata": {
            "title": "Global-to-Local Real Estate Network Knowledge Graph",
            "version": "2.0.0",
            "generated_at": datetime.now().isoformat(),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "top_converged_hub_regions": top_converged_regions[:3],
            "common_converged_features": [
                "1. 대규모 앵커 국공유지(철도정비창/삼표/준공업지) 인접성 (Mega Land Catalyst)",
                "2. 3개 이상 노선 교차 메가 환승 결절점 반경 500m (Transit Convergence)",
                "3. 평당 분양가 7,000만+ 지불 가능한 고소득 코호트 배후 (Solvency Absorption)",
                "4. 기존 용적률 150% 이하 원시 대지 및 쪼개기 없는 소유권 집중 (Pre-FAR Gap & Anti-Fragmentation)"
            ]
        },
        "nodes": nodes,
        "edges": edges
    }

    with open(graph_file, "w", encoding="utf-8") as f:
        json.dump(graph_payload, f, indent=2, ensure_ascii=False)

    return graph_payload


if __name__ == "__main__":
    res = build_real_estate_network_graph()
    print(f"Successfully generated network graph with {res['metadata']['total_nodes']} nodes and {res['metadata']['total_edges']} edges.")
