"""Competition graph — stores as nodes, catchment overlaps as weighted edges.

Uses NetworkX when available for centrality/clustering metrics; otherwise falls
back to a lightweight adjacency-dict implementation so the core metrics
(degree, competitive pressure) still work without the dependency.
"""
import logging
from typing import List, Dict, Any, Optional

from backend.app.competition.overlap import overlap_circles

logger = logging.getLogger(__name__)


def build_edges(
    stores: List[Dict[str, Any]],
    min_overlap: float = 0.05,
) -> List[Dict[str, Any]]:
    """Edge for every store pair whose catchments overlap above min_overlap (Jaccard)."""
    edges = []
    for i in range(len(stores)):
        for j in range(i + 1, len(stores)):
            a, b = stores[i], stores[j]
            ov = overlap_circles(
                a["lat"], a["lon"], a.get("catchment_radius_m", 800),
                b["lat"], b["lon"], b.get("catchment_radius_m", 800),
            )
            if ov["jaccard"] >= min_overlap:
                edges.append({
                    "source": a["id"], "target": b["id"],
                    "weight": ov["jaccard"], "overlap_ratio": ov["overlap_ratio"],
                    "distance_m": ov["distance_m"],
                })
    return edges


def competitive_pressure(stores: List[Dict[str, Any]], min_overlap: float = 0.05) -> Dict[Any, Dict[str, Any]]:
    """Per-store pressure = sum of overlap weights with all neighbours."""
    edges = build_edges(stores, min_overlap)
    pressure: Dict[Any, Dict[str, Any]] = {
        s["id"]: {"degree": 0, "pressure": 0.0, "neighbors": []} for s in stores
    }
    for e in edges:
        for src, dst in ((e["source"], e["target"]), (e["target"], e["source"])):
            pressure[src]["degree"] += 1
            pressure[src]["pressure"] += e["weight"]
            pressure[src]["neighbors"].append(dst)
    for v in pressure.values():
        v["pressure"] = round(v["pressure"], 4)
    return pressure


def build_graph(stores: List[Dict[str, Any]], min_overlap: float = 0.05) -> Dict[str, Any]:
    """Return nodes, edges, per-store pressure, and (if NetworkX present) centrality."""
    edges = build_edges(stores, min_overlap)
    pressure = competitive_pressure(stores, min_overlap)

    centrality: Optional[Dict[Any, float]] = None
    components: Optional[int] = None
    try:
        import networkx as nx
        g = nx.Graph()
        g.add_nodes_from(s["id"] for s in stores)
        for e in edges:
            g.add_edge(e["source"], e["target"], weight=e["weight"])
        centrality = {k: round(v, 4) for k, v in nx.degree_centrality(g).items()}
        components = nx.number_connected_components(g)
    except Exception as e:  # noqa: BLE001
        logger.info("NetworkX unavailable, returning basic graph metrics (%s)", e)

    return {
        "nodes": [{"id": s["id"], **pressure[s["id"]]} for s in stores],
        "edges": edges,
        "num_clusters": components,
        "centrality": centrality,
        "most_pressured": max(pressure.items(), key=lambda kv: kv[1]["pressure"])[0] if pressure else None,
    }
