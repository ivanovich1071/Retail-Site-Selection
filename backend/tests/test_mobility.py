from backend.app.mobility.trajectory import clean_trajectory, trajectory_stats
from backend.app.mobility.staypoints import detect_staypoints, dwell_summary
from backend.app.mobility.od_matrix import build_od_matrix, top_flows
from backend.app.mobility.flow_analysis import footfall, commuter_ratio, zone_flow_profiles


# ── trajectory cleaning ──────────────────────────────────────────────
def test_clean_removes_speed_spike():
    pts = [
        {"lat": 53.90, "lon": 27.56, "t": 0},
        {"lat": 53.90, "lon": 27.561, "t": 10},   # plausible
        {"lat": 55.00, "lon": 30.00, "t": 11},    # teleport → drop
        {"lat": 53.901, "lon": 27.562, "t": 30},
    ]
    cleaned = clean_trajectory(pts)
    assert all(p["lat"] < 54 for p in cleaned)


def test_clean_sorts_chronologically():
    pts = [
        {"lat": 53.90, "lon": 27.56, "t": 30},
        {"lat": 53.901, "lon": 27.561, "t": 0},
    ]
    cleaned = clean_trajectory(pts)
    assert cleaned[0]["t"] <= cleaned[-1]["t"]


def test_trajectory_stats():
    pts = [
        {"lat": 53.90, "lon": 27.56, "t": 0},
        {"lat": 53.901, "lon": 27.56, "t": 100},
    ]
    s = trajectory_stats(pts)
    assert s["distance_m"] > 0
    assert s["duration_s"] == 100
    assert s["mean_speed_m_s"] > 0


# ── staypoints ───────────────────────────────────────────────────────
def test_detect_staypoint_dwell():
    # 6 points clustered over 600s at one spot, then move away
    pts = [{"lat": 53.90, "lon": 27.56, "t": i * 120} for i in range(6)]
    pts.append({"lat": 53.91, "lon": 27.58, "t": 800})
    stays = detect_staypoints(pts, max_dist_m=50, min_duration_s=300)
    assert len(stays) == 1
    assert stays[0]["dwell_time_s"] >= 300


def test_no_staypoint_when_moving():
    pts = [{"lat": 53.90 + i * 0.01, "lon": 27.56, "t": i * 120} for i in range(5)]
    assert detect_staypoints(pts, max_dist_m=50, min_duration_s=300) == []


def test_dwell_summary_empty():
    assert dwell_summary([])["count"] == 0


# ── OD matrix ────────────────────────────────────────────────────────
def test_od_matrix_counts_transitions():
    # two trips A→B; staypoints far enough apart to land in different hexes
    trip = [
        {"lat": 53.90, "lon": 27.56, "t": 0},
        {"lat": 53.93, "lon": 27.62, "t": 600},
    ]
    od = build_od_matrix([trip, trip], resolution=8)
    assert od["total_trips"] == 2
    assert len(od["zones"]) == 2
    flows = top_flows(od)
    assert flows[0]["count"] == 2


# ── flow analysis ────────────────────────────────────────────────────
def test_footfall_counts_passing_trajectories():
    near = [{"lat": 53.9000, "lon": 27.5600, "t": 3600}]
    far = [{"lat": 53.9500, "lon": 27.7000, "t": 3600}]
    res = footfall([near, far], 53.90, 27.56, radius_m=100)
    assert res["unique_trajectories"] == 1


def test_commuter_ratio_classification():
    assert commuter_ratio(80, 20)["type"] == "destination"
    assert commuter_ratio(20, 80)["type"] == "origin"
    assert commuter_ratio(50, 50)["type"] == "balanced"


def test_zone_flow_profiles():
    od = {"zones": ["x"], "inflow": {"x": 10}, "outflow": {"x": 2}}
    profiles = zone_flow_profiles(od)
    assert profiles["x"]["type"] == "destination"
