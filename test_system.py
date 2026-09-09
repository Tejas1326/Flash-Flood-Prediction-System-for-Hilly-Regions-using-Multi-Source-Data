from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

VILLAGES_TO_TEST = [
    ("chiplun", 17.5323, 73.5177),
    ("mahad", 18.0827, 73.4188),
    ("taliye", 18.1034, 73.5852),
    ("poladpur", 17.9806, 73.4664),
    ("khed", 17.7214, 73.3905),
    ("dapoli", 17.7621, 73.1856),
    ("guhagar", 17.4855, 73.1934),
]

def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert "Konkan Flash-Flood Early Warning System" in response.text

def test_predict_risk_all_villages():
    predictions = {}
    for village_id, lat, lon in VILLAGES_TO_TEST:
        resp = client.post("/predict-risk", json={"village_id": village_id, "lat": lat, "lon": lon})
        assert resp.status_code == 200
        data = resp.json()
        assert data["village_id"] == village_id
        assert 0.0 <= data["probability"] <= 1.0
        assert data["risk"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        assert data["estimated_warning_window_min"] > 0
        assert 0.0 <= data["confidence"] <= 1.0
        predictions[village_id] = data

    # Verify Chiplun is critical / highest risk
    highest = max(predictions.values(), key=lambda x: x["probability"])
    assert highest["village_id"] == "chiplun"
    assert highest["risk"] == "CRITICAL"
    assert 0.75 <= highest["probability"] <= 0.95
    assert 15 <= highest["estimated_warning_window_min"] <= 35


def test_api_monitored_villages():
    resp = client.get("/api/villages")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6
    chiplun = next(v for v in data if v["village_id"] == "chiplun")
    assert chiplun["name"] == "Chiplun"
    assert "elevation" in chiplun and "slope" in chiplun
    assert chiplun["elevation"] < 0  # Low-lying alluvial basin


def test_api_designated_shelters():
    resp = client.get("/api/shelters")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    shelter_names = [s["name"] for s in data]
    assert "Mahad Relief Shelter" in shelter_names
    assert "Chiplun Shelter" in shelter_names


def test_api_all_villages_risk():
    resp = client.get("/api/villages/all-risks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6
    assert data[0]["village_id"] == "chiplun"
    assert data[0]["risk"] == "CRITICAL"

def test_predict_risk_fallback_unlisted_village():
    resp = client.post("/predict-risk", json={"village_id": "unknown_village", "lat": 17.65, "lon": 73.45})
    assert resp.status_code == 200
    data = resp.json()
    assert data["village_id"] == "unknown_village"
    assert 0.0 <= data["probability"] <= 1.0
    assert data["risk"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]

def test_dijkstra_evacuation_route():
    payload = {
        "origin": {"lat": 17.5323, "lng": 73.5177},
        "destination": {"lat": 17.5580, "lng": 73.5420},
        "weight": "length"
    }
    resp = client.post("/api/routes/evacuation", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["distance_km"] > data["straight_distance_km"]
    assert data["nodes_count"] >= 20
    assert len(data["route"]) >= 50
    assert any("Highway" in name or "Road" in name or "Naka" in name for name in data["road_names"])


def test_multi_origin_evacuation_routes():
    import time
    from routing import compute_multi_origin_routes, compute_dijkstra_evacuation_route, ORIGIN_LOCALITIES

    dest_lat = 17.5580
    dest_lon = 73.5420

    # 1. API Call test with default origins
    payload = {
        "destination": {"lat": dest_lat, "lng": dest_lon}
    }
    resp = client.post("/api/routes/evacuation/multi", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "routes" in data
    routes = data["routes"]
    assert len(routes) == len(ORIGIN_LOCALITIES)

    distances = []
    for r in routes:
        assert "origin_name" in r
        assert r["status"] == "success"
        assert r["distance_km"] > r["straight_distance_km"], f"Route for {r['origin_name']} did not use real road geometry"
        assert r["distance_km"] != r["straight_distance_km"], f"Route for {r['origin_name']} equaled straight distance"
        assert len(r["road_names"]) > 0
        distances.append(r["distance_km"])

    # Confirm distances differ sensibly across origins
    assert max(distances) > min(distances), "All origin distances were identical"
    print(f"\n[Multi-Route] Evacuation distances computed for {len(routes)} origins: {distances} km")

    # 2. Timing benchmark comparison: Single Reversed Dijkstra vs. Naive per-origin loop
    # Benchmark Single Reversed Dijkstra approach
    t0 = time.perf_counter()
    res_single_dijkstra = compute_multi_origin_routes(
        origins=ORIGIN_LOCALITIES,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        weight_param="length"
    )
    t_single_dijkstra = (time.perf_counter() - t0) * 1000.0

    # Benchmark Naive per-origin loop calling compute_dijkstra_evacuation_route() repeatedly
    t0 = time.perf_counter()
    res_naive_loop = []
    for orig in ORIGIN_LOCALITIES:
        res = compute_dijkstra_evacuation_route(
            orig_lat=orig["lat"],
            orig_lon=orig["lon"],
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            weight_param="length"
        )
        res_naive_loop.append(res)
    t_naive_loop = (time.perf_counter() - t0) * 1000.0

    print(f"[Benchmark] Single Reversed Dijkstra pass time for {len(ORIGIN_LOCALITIES)} origins: {t_single_dijkstra:.2f} ms")
    print(f"[Benchmark] Naive per-origin loop re-running Dijkstra time: {t_naive_loop:.2f} ms")
    if t_naive_loop > 0:
        speedup = t_naive_loop / max(t_single_dijkstra, 0.001)
        print(f"[Benchmark] Speedup factor: {speedup:.2f}x faster using Single Reversed Dijkstra")

    # 3. Custom origins API test
    custom_origins = [
        {"name": "Custom Spot A", "lat": 17.5300, "lng": 73.5200},
        {"name": "Custom Spot B", "lat": 17.5600, "lng": 73.5100}
    ]
    payload_custom = {
        "destination": {"lat": dest_lat, "lng": dest_lon},
        "origins": custom_origins
    }
    resp_custom = client.post("/api/routes/evacuation/multi", json=payload_custom)
    assert resp_custom.status_code == 200
    custom_routes = resp_custom.json()["routes"]
    assert len(custom_routes) == 2
    assert custom_routes[0]["origin_name"] == "Custom Spot A"
    assert custom_routes[1]["origin_name"] == "Custom Spot B"


def test_risk_propagation_chiplun():
    resp = client.get("/api/risk/propagation/chiplun")
    assert resp.status_code == 200
    data = resp.json()

    assert "source_village" in data
    assert data["source_village"]["name"] == "Chiplun"
    assert data["source_village"]["current_risk"] == "CRITICAL"

    assert "estimated_next_affected" in data
    next_list = data["estimated_next_affected"]
    assert len(next_list) == 6

    # Verify top propagation candidate for Chiplun is Khed (Jagbudi/Vashishti catchment, ~25 km away)
    top_candidate = next_list[0]
    assert top_candidate["name"] == "Khed"
    assert top_candidate["concern_level"] == "Elevated"
    assert top_candidate["distance_km"] < 30.0

    # Verify disclaimer note presence and contents
    assert "note" in data
    assert "Not a hydraulic simulation" in data["note"]
    assert "terrain and spatial proximity" in data["note"]

    # Verify factors reporting
    assert "spatial proximity" in top_candidate["factors_considered"]
    assert "elevation / terrain slope profile" in top_candidate["unavailable_factors"]

    # Test 404 for unknown village
    resp_404 = client.get("/api/risk/propagation/unknown_location")
    assert resp_404.status_code == 404


def test_safe_evacuation_route_mahad_to_mahad_shelter():
    resp = client.get("/api/evacuation-route?start=Mahad&destination=Mahad")
    assert resp.status_code == 200, f"Failed with {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["start"]["name"] == "Mahad"
    assert data["destination"]["name"] == "Mahad Relief Shelter"
    assert data["distance_km"] > 0
    assert len(data["route"]) > 10


def test_safe_evacuation_route_taliye_to_mahad():
    resp = client.get("/api/evacuation-route?start=Taliye&destination=Mahad")
    assert resp.status_code == 200, f"Failed with {resp.status_code}: {resp.text}"
    data = resp.json()

    # 1. Location and Shelter verification
    assert data["start"]["name"] == "Taliye"
    assert abs(data["start"]["latitude"] - 18.1034) < 0.01
    assert abs(data["start"]["longitude"] - 73.5852) < 0.01

    assert data["destination"]["name"] == "Mahad Relief Shelter"
    assert abs(data["destination"]["latitude"] - 18.1050) < 0.01
    assert abs(data["destination"]["longitude"] - 73.4350) < 0.01

    # 2. Real road network validation (not straight line)
    straight_km = 16.0  # approximate euclidean straight distance
    assert data["distance_km"] > straight_km, f"Route distance {data['distance_km']}km was not longer than straight-line distance {straight_km}km"
    assert data["distance_km"] >= 20.0
    assert len(data["route"]) >= 25, "Route did not contain detailed road network coordinates"
    assert data["estimated_time_min"] > 0

    # 3. Risk & warnings validation
    assert data["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert data["recommended"] is True
    assert "warnings" in data
    assert len(data["warnings"]) >= 2
    assert any("Mahad Relief Shelter" in w or "shelter" in w.lower() for w in data["warnings"])

    # 4. Candidates list validation
    assert "candidates" in data
    assert len(data["candidates"]) >= 2, "Expected at least Safest and Shortest candidate routes"
    safest_cand = next((c for c in data["candidates"] if c["recommended"]), None)
    assert safest_cand is not None
    assert safest_cand["id"] == "safest"


def test_safe_evacuation_route_chiplun_to_chiplun_shelter():
    resp = client.get("/api/evacuation-route?start=Chiplun&destination=Chiplun%20Shelter")
    assert resp.status_code == 200, f"Failed with {resp.status_code}: {resp.text}"
    data = resp.json()

    # 1. Location and Shelter verification
    assert data["start"]["name"] == "Chiplun"
    assert abs(data["start"]["latitude"] - 17.5323) < 0.01
    assert abs(data["start"]["longitude"] - 73.5177) < 0.01

    assert "Chiplun" in data["destination"]["name"]
    assert abs(data["destination"]["latitude"] - 17.5580) < 0.01
    assert abs(data["destination"]["longitude"] - 73.5420) < 0.01

    # 2. Real road network validation (not straight line)
    assert data["distance_km"] > 3.0
    assert len(data["route"]) >= 25, "Route did not contain detailed road network coordinates"
    assert data["estimated_time_min"] > 0

    # 3. Risk & warnings validation
    assert data["risk_level"] in ["HIGH", "CRITICAL"]
    assert data["recommended"] is True
    assert "warnings" in data
    assert len(data["warnings"]) >= 1
    assert any("CRITICAL FLOOD RISK" in w or "critical" in w.lower() for w in data["warnings"])

    # 4. Candidates list validation
    assert "candidates" in data
    assert len(data["candidates"]) >= 1
    safest_cand = next((c for c in data["candidates"] if c["recommended"]), None)
    assert safest_cand is not None
    assert safest_cand["id"] == "safest"


def test_geocoding_and_shelter_validation():
    from routing import geocode_location, DESIGNATED_SHELTERS

    # 1. Test Taliye geocoding
    taliye = geocode_location("Taliye", expected_district="Raigad", expected_state="Maharashtra")
    assert abs(taliye["latitude"] - 18.1034) < 0.01
    assert abs(taliye["longitude"] - 73.5852) < 0.01

    # 2. Test Mahad Shelter geocoding
    shelter = geocode_location("Mahad Relief Shelter", expected_district="Raigad", expected_state="Maharashtra")
    assert abs(shelter["latitude"] - 18.1050) < 0.01
    assert abs(shelter["longitude"] - 73.4350) < 0.01

    # 3. Test Chiplun Shelter geocoding
    chiplun_shelter = geocode_location("Chiplun Relief Shelter", expected_district="Ratnagiri", expected_state="Maharashtra")
    assert abs(chiplun_shelter["latitude"] - 17.5580) < 0.01
    assert abs(chiplun_shelter["longitude"] - 73.5420) < 0.01

    # 4. Test invalid location handling via API (404 error)
    resp_invalid = client.get("/api/evacuation-route?start=NonExistentVillage999&destination=Mahad")
    assert resp_invalid.status_code == 404
    assert "could not be resolved" in resp_invalid.json()["detail"]


def test_candidate_routes_safety_comparison():
    resp = client.get("/api/evacuation-route?start=Taliye&destination=Mahad")
    assert resp.status_code == 200
    data = resp.json()
    candidates = data["candidates"]

    safest = next(c for c in candidates if c["id"] == "safest")
    shortest = next((c for c in candidates if c["id"] == "shortest"), None)

    if shortest:
        # The shortest route uses direct bridges/chokepoints
        assert shortest["recommended"] is False
        assert shortest["distance_km"] <= safest["distance_km"] + 0.1
        # Safest route minimizes or accounts for hazardous bridge crossings
        print(f"[Safety Comparison] Safest: {safest['distance_km']}km, {safest['bridge_crossings']} bridges vs Shortest: {shortest['distance_km']}km, {shortest['bridge_crossings']} bridges")


if __name__ == "__main__":
    print("Running system validation tests...")
    test_root_serves_html()
    print("[PASS] test_root_serves_html passed")
    test_predict_risk_all_villages()
    print("[PASS] test_predict_risk_all_villages passed")
    test_predict_risk_fallback_unlisted_village()
    print("[PASS] test_predict_risk_fallback_unlisted_village passed")
    test_dijkstra_evacuation_route()
    print("[PASS] test_dijkstra_evacuation_route passed")
    test_multi_origin_evacuation_routes()
    print("[PASS] test_multi_origin_evacuation_routes passed")
    test_risk_propagation_chiplun()
    print("[PASS] test_risk_propagation_chiplun passed")
    test_safe_evacuation_route_taliye_to_mahad()
    print("[PASS] test_safe_evacuation_route_taliye_to_mahad passed")
    test_safe_evacuation_route_chiplun_to_chiplun_shelter()
    print("[PASS] test_safe_evacuation_route_chiplun_to_chiplun_shelter passed")
    test_geocoding_and_shelter_validation()
    print("[PASS] test_geocoding_and_shelter_validation passed")
    test_candidate_routes_safety_comparison()
    print("[PASS] test_candidate_routes_safety_comparison passed")
    print("\nAll validation tests passed successfully!")

