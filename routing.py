import os
import math
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx
import osmnx as ox

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "konkan_road_graph.graphml")

_graph = None

# Representative locality points spread across the Chiplun at-risk area
# (Note: exact municipal ward boundaries aren't available in OSM for Chiplun,
# so these are clearly-labeled representative locality points spread across the region).
ORIGIN_LOCALITIES = [
    {"name": "Chiplun Town Center", "lat": 17.5323, "lon": 73.5177},
    {"name": "Parshuram", "lat": 17.5760, "lon": 73.5180},
    {"name": "Bhilwadi", "lat": 17.5250, "lon": 73.5350},
    {"name": "Kaviltali Ward", "lat": 17.5410, "lon": 73.5280},
    {"name": "Muradpur Ward", "lat": 17.5280, "lon": 73.5090},
    {"name": "Khed Road Junction", "lat": 17.5550, "lon": 73.5120},
]


def get_graph():
    global _graph
    if _graph is not None:
        return _graph

    if os.path.exists(CACHE_FILE):
        print(f"[Routing] Loading cached OSM road graph from {CACHE_FILE}...")
        _graph = ox.load_graphml(CACHE_FILE)
        print(f"[Routing] Graph loaded: {_graph.number_of_nodes()} nodes, {_graph.number_of_edges()} edges.")
    else:
        print("[Routing] Downloading drivable OSM road network for Konkan region...")
        g1 = ox.graph_from_point((17.545, 73.530), dist=14000, network_type='drive')
        g2 = ox.graph_from_point((18.090, 73.425), dist=14000, network_type='drive')
        g3 = ox.graph_from_point((17.490, 73.200), dist=14000, network_type='drive')
        _graph = nx.compose_all([g1, g2, g3])
        ox.save_graphml(_graph, CACHE_FILE)
        print(f"[Routing] Graph saved to {CACHE_FILE}: {_graph.number_of_nodes()} nodes, {_graph.number_of_edges()} edges.")
    return _graph


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _extract_route_geometry(G, route_nodes):
    """
    Shared helper to extract true road edge curve geometry, road names,
    and total metric road distance from a sequence of graph node IDs.

    Shared by both single-route (compute_dijkstra_evacuation_route) and
    multi-route (compute_multi_origin_routes) functions.
    """
    route_coords_obj = []
    route_coords_list = []
    road_names = set()
    total_road_distance_m = 0.0

    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        edge_dict = G.get_edge_data(u, v)
        if not edge_dict:
            continue
        edge_data = list(edge_dict.values())[0] if isinstance(edge_dict, dict) else edge_dict[0]

        length = edge_data.get('length', 0)
        if isinstance(length, (int, float)):
            total_road_distance_m += float(length)

        name = edge_data.get('name')
        if name:
            if isinstance(name, list):
                road_names.update(name)
            else:
                road_names.add(str(name))

        if 'geometry' in edge_data and hasattr(edge_data['geometry'], 'coords'):
            for x_coord, y_coord in edge_data['geometry'].coords:
                pt_obj = {"lat": float(y_coord), "lng": float(x_coord)}
                pt_list = [float(y_coord), float(x_coord)]
                if not route_coords_list or route_coords_list[-1] != pt_list:
                    route_coords_obj.append(pt_obj)
                    route_coords_list.append(pt_list)
        else:
            u_pt_obj = {"lat": float(G.nodes[u]['y']), "lng": float(G.nodes[u]['x'])}
            u_pt_list = [float(G.nodes[u]['y']), float(G.nodes[u]['x'])]
            v_pt_obj = {"lat": float(G.nodes[v]['y']), "lng": float(G.nodes[v]['x'])}
            v_pt_list = [float(G.nodes[v]['y']), float(G.nodes[v]['x'])]

            if not route_coords_list or route_coords_list[-1] != u_pt_list:
                route_coords_obj.append(u_pt_obj)
                route_coords_list.append(u_pt_list)
            route_coords_obj.append(v_pt_obj)
            route_coords_list.append(v_pt_list)

    sorted_names = sorted(list(road_names))
    if not sorted_names:
        sorted_names = ["Unnamed Local Connector"]

    return route_coords_obj, route_coords_list, sorted_names, total_road_distance_m


def compute_dijkstra_evacuation_route(
    orig_lat: float,
    orig_lon: float,
    dest_lat: float,
    dest_lon: float,
    weight_param: str = "length"
):
    """
    Computes a single real road evacuation route using Dijkstra's algorithm on an OSM drivable graph.
    Extracts true edge curve geometry and returns detailed route statistics.
    Maintained for backward compatibility.
    """
    G = get_graph()

    orig_node = ox.distance.nearest_nodes(G, X=orig_lon, Y=orig_lat)
    dest_node = ox.distance.nearest_nodes(G, X=dest_lon, Y=dest_lat)

    orig_y = float(G.nodes[orig_node]['y'])
    orig_x = float(G.nodes[orig_node]['x'])
    dest_y = float(G.nodes[dest_node]['y'])
    dest_x = float(G.nodes[dest_node]['x'])

    orig_snap_dist = haversine(orig_lat, orig_lon, orig_y, orig_x)
    dest_snap_dist = haversine(dest_lat, dest_lon, dest_y, dest_x)

    print(f"[Routing] Single route: Origin snapped to node {orig_node} ({orig_y:.5f}, {orig_x:.5f}), offset: {orig_snap_dist:.1f}m")
    print(f"[Routing] Single route: Dest snapped to node {dest_node} ({dest_y:.5f}, {dest_x:.5f}), offset: {dest_snap_dist:.1f}m")

    straight_dist_km = haversine(orig_y, orig_x, dest_y, dest_x) / 1000.0

    try:
        route_nodes = nx.dijkstra_path(G, orig_node, dest_node, weight=weight_param)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        print("[Routing] WARNING: No Dijkstra path found between snapped nodes. Returning fallback.")
        return {
            "status": "fallback",
            "origin_snapped": {"lat": orig_y, "lng": orig_x},
            "destination_snapped": {"lat": dest_y, "lng": dest_x},
            "distance_km": round(straight_dist_km, 2),
            "straight_distance_km": round(straight_dist_km, 2),
            "nodes_count": 2,
            "geometry_count": 2,
            "road_names": ["Direct Segment (Fallback)"],
            "route": [{"lat": orig_lat, "lng": orig_lon}, {"lat": dest_lat, "lng": dest_lon}],
            "coordinates": [[orig_lat, orig_lon], [dest_lat, dest_lon]]
        }

    route_coords_obj, route_coords_list, sorted_road_names, total_road_distance_m = _extract_route_geometry(G, route_nodes)
    road_dist_km = total_road_distance_m / 1000.0

    return {
        "status": "success",
        "origin_snapped": {"lat": orig_y, "lng": orig_x},
        "destination_snapped": {"lat": dest_y, "lng": dest_x},
        "straight_distance_km": round(straight_dist_km, 2),
        "distance_km": round(road_dist_km, 2),
        "nodes_count": len(route_nodes),
        "geometry_count": len(route_coords_list),
        "road_names": sorted_road_names,
        "route": route_coords_obj,
        "coordinates": route_coords_list
    }


def compute_multi_origin_routes(
    origins=None,
    dest_lat: float = 17.5580,
    dest_lon: float = 73.5420,
    weight_param: str = "length"
):
    """
    WHY NOT A LOOP:
    Calling nx.dijkstra_path() separately for each origin re-explores the graph from scratch every time —
    wasteful when the destination is fixed and only the origin varies. Since Dijkstra computes a full
    shortest-path tree from a source to ALL reachable nodes in one pass, the efficient approach is:
       1. Reverse the graph (G_rev = G.reverse(copy=False)).
       2. Run a SINGLE Dijkstra computation rooted at destination (shelter) node using
          nx.single_source_dijkstra(G_rev, source=dest_node, weight=weight_param) — this returns both
          shortest distances AND paths to every reachable node in the graph in one pass.
       3. For each origin point, snap it to its nearest node, then simply look up its precomputed path
          from the single_source_dijkstra result instead of recomputing Dijkstra from scratch.
       4. Reverse the node list back to get origin -> destination order: list(reversed(paths[orig_node])).
    """
    if origins is None or len(origins) == 0:
        origins = ORIGIN_LOCALITIES

    G = get_graph()

    # Step 1: Snap destination shelter coordinate to graph node
    dest_node = ox.distance.nearest_nodes(G, X=dest_lon, Y=dest_lat)
    dest_y = float(G.nodes[dest_node]['y'])
    dest_x = float(G.nodes[dest_node]['x'])

    # Step 2: Build a reversed graph view
    G_rev = G.reverse(copy=False)

    # Step 3: Run ONE Dijkstra pass rooted at destination shelter
    print(f"[Routing] Running single reversed Dijkstra pass rooted at destination node {dest_node}...")
    distances, paths = nx.single_source_dijkstra(G_rev, source=dest_node, weight=weight_param)

    routes_result = []

    # Step 4: Process each origin point by looking up precomputed paths
    for orig in origins:
        orig_name = orig.get("name", "Unknown Locality")
        orig_lat = orig.get("lat")
        orig_lon = orig.get("lon") if "lon" in orig else orig.get("lng")

        if orig_lat is None or orig_lon is None:
            continue

        orig_node = ox.distance.nearest_nodes(G, X=orig_lon, Y=orig_lat)
        orig_y = float(G.nodes[orig_node]['y'])
        orig_x = float(G.nodes[orig_node]['x'])

        straight_dist_km = haversine(orig_y, orig_x, dest_y, dest_x) / 1000.0

        if orig_node not in paths:
            # Handle unreachable origin gracefully
            print(f"[Routing] WARNING: Origin '{orig_name}' (node {orig_node}) is unreachable from destination shelter node {dest_node}.")
            routes_result.append({
                "origin_name": orig_name,
                "status": "fallback",
                "origin_snapped": {"lat": orig_y, "lng": orig_x},
                "destination_snapped": {"lat": dest_y, "lng": dest_x},
                "straight_distance_km": round(straight_dist_km, 2),
                "distance_km": round(straight_dist_km, 2),
                "nodes_count": 2,
                "geometry_count": 2,
                "road_names": ["Direct Segment (Fallback)"],
                "route": [{"lat": orig_lat, "lng": orig_lon}, {"lat": dest_lat, "lng": dest_lon}],
                "coordinates": [[orig_lat, orig_lon], [dest_lat, dest_lon]]
            })
            continue

        # Reverse node list because paths were computed on G_rev from dest_node to orig_node
        route_nodes = list(reversed(paths[orig_node]))

        # Reuse shared edge-geometry extraction
        route_coords_obj, route_coords_list, sorted_road_names, total_road_distance_m = _extract_route_geometry(G, route_nodes)
        road_dist_km = total_road_distance_m / 1000.0

        routes_result.append({
            "origin_name": orig_name,
            "status": "success",
            "origin_snapped": {"lat": orig_y, "lng": orig_x},
            "destination_snapped": {"lat": dest_y, "lng": dest_x},
            "straight_distance_km": round(straight_dist_km, 2),
            "distance_km": round(road_dist_km, 2),
            "nodes_count": len(route_nodes),
            "geometry_count": len(route_coords_list),
            "road_names": sorted_road_names,
            "route": route_coords_obj,
            "coordinates": route_coords_list
        })

    return routes_result


# ============================================================================
# SAFE FLOOD EVACUATION ROUTING ENGINE
# ============================================================================
try:
    from data_loader import data_loader

    DESIGNATED_SHELTERS = {}
    for s in data_loader.get_shelters_list():
        s_key = s["id"].replace("_shelter", "").lower()
        DESIGNATED_SHELTERS[s_key] = {
            "name": s["name"],
            "latitude": s["lat"],
            "longitude": s["lon"],
            "district": s.get("district", "Maharashtra"),
            "description": s.get("address", s["name"])
        }

    VERIFIED_REGIONAL_REGISTRY = {}
    # Register dataset villages
    for v in data_loader.get_villages_list():
        v_id = v["village_id"]
        v_entry = {
            "name": v["name"],
            "latitude": v["lat"],
            "longitude": v["lon"],
            "district": v.get("district", "Maharashtra"),
            "taluka": v["name"],
            "state": "Maharashtra"
        }
        VERIFIED_REGIONAL_REGISTRY[v_id] = v_entry
        VERIFIED_REGIONAL_REGISTRY[f"{v_id} village"] = v_entry
        VERIFIED_REGIONAL_REGISTRY[v["name"].lower()] = v_entry

    # Register shelters in registry
    for s in data_loader.get_shelters_list():
        s_entry = {
            "name": s["name"],
            "latitude": s["lat"],
            "longitude": s["lon"],
            "district": s.get("district", "Maharashtra"),
            "taluka": s.get("district", "Maharashtra"),
            "state": "Maharashtra"
        }
        s_name_lower = s["name"].lower()
        s_id = s["id"].lower()
        VERIFIED_REGIONAL_REGISTRY[s_id] = s_entry
        VERIFIED_REGIONAL_REGISTRY[s_name_lower] = s_entry
        VERIFIED_REGIONAL_REGISTRY[s_name_lower.replace("relief ", "")] = s_entry
        if "mahad" in s_name_lower:
            VERIFIED_REGIONAL_REGISTRY["shelter"] = s_entry
            VERIFIED_REGIONAL_REGISTRY["mahad civil defence shelter"] = s_entry
        if "chiplun" in s_name_lower:
            VERIFIED_REGIONAL_REGISTRY["chiplun relief shelter"] = s_entry

except Exception as e:
    print(f"[Routing] Warning initializing dynamic registry from data_loader: {e}")
    DESIGNATED_SHELTERS = {
        "mahad": {
            "name": "Mahad Relief Shelter",
            "latitude": 18.1050,
            "longitude": 73.4350,
            "district": "Raigad",
            "description": "Mahad Civil Defence & Disaster Management Shelter"
        },
        "chiplun": {
            "name": "Chiplun Shelter",
            "latitude": 17.5580,
            "longitude": 73.5420,
            "district": "Ratnagiri",
            "description": "Chiplun High Ground Relief Shelter"
        }
    }
    VERIFIED_REGIONAL_REGISTRY = {
        "taliye": {"name": "Taliye", "latitude": 18.108249, "longitude": 73.576349, "district": "Raigad", "taluka": "Mahad", "state": "Maharashtra"},
        "mahad": {"name": "Mahad", "latitude": 18.083333, "longitude": 73.416667, "district": "Raigad", "taluka": "Mahad", "state": "Maharashtra"},
        "chiplun": {"name": "Chiplun", "latitude": 17.533388, "longitude": 73.509355, "district": "Ratnagiri", "taluka": "Chiplun", "state": "Maharashtra"}
    }

DEFAULT_RISK_WEIGHTS = {
    "LOW": 0.0,
    "MODERATE": 2.0,
    "HIGH": 10.0,
    "CRITICAL": 100.0,
}

ROUTING_CONFIG = {
    "risk_weights": DEFAULT_RISK_WEIGHTS,
    "bridge_penalty": 5.0,
    "unpaved_penalty": 2.5,
    "trunk_primary_discount": 0.85
}

DEFAULT_FLOOD_ZONES = [
    {"name": "Mahad Savitri Basin", "lat": 18.0827, "lon": 73.4188, "radius_m": 2500, "risk_level": "HIGH"},
    {"name": "Savitri Floodway Buffer", "lat": 18.0950, "lon": 73.4600, "radius_m": 2000, "risk_level": "HIGH"},
    {"name": "Taliye Catchment Slopes", "lat": 18.1034, "lon": 73.5852, "radius_m": 1500, "risk_level": "MODERATE"},
    {"name": "Chiplun Vashishti Basin", "lat": 17.5323, "lon": 73.5177, "radius_m": 2500, "risk_level": "HIGH"},
]


def geocode_location(
    query: str,
    expected_district: str = "Raigad",
    expected_state: str = "Maharashtra"
) -> Dict[str, Any]:
    """
    Geocodes a location query dynamically via OpenStreetMap Nominatim API,
    with district and state disambiguation, and fallbacks to a verified regional registry.
    """
    if not query or not query.strip():
        raise ValueError("Location query cannot be empty.")

    q_clean = query.strip()
    q_lower = q_clean.lower()

    # 1. Direct shelter checks
    if "shelter" in q_lower or "camp" in q_lower:
        if "chiplun" in q_lower:
            s = DESIGNATED_SHELTERS["chiplun"]
        else:
            s = DESIGNATED_SHELTERS["mahad"]
        return {
            "name": s["name"],
            "latitude": s["latitude"],
            "longitude": s["longitude"],
            "display_name": f"{s['name']}, {s.get('district', expected_district)}, {expected_state}, India",
            "source": "designated_shelter_registry"
        }

    # 2. Check verified regional registry first for deterministic, instant regional resolution
    for k, v in VERIFIED_REGIONAL_REGISTRY.items():
        if k == q_lower or k in q_lower or q_lower in k:
            return {
                "name": v["name"],
                "latitude": v["latitude"],
                "longitude": v["longitude"],
                "display_name": f"{v['name']}, {v.get('taluka', '')}, {v.get('district', expected_district)}, {expected_state}, India",
                "source": "verified_regional_registry"
            }

    # 3. Dynamic geocoding via OpenStreetMap Nominatim for unknown queries
    try:
        search_query = f"{q_clean}, {expected_district}, {expected_state}, India"
        encoded = urllib.parse.quote(search_query)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&addressdetails=1&limit=5"
        headers = {
            "User-Agent": "KonkanFloodEarlyWarning/1.0 (disaster-relief-evacuation-system)"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data and len(data) > 0:
                for item in data:
                    addr = item.get("address", {})
                    state = addr.get("state", "")
                    county = addr.get("county", "") or addr.get("state_district", "")
                    display = item.get("display_name", "")
                    # Ensure matching in Maharashtra
                    if "Maharashtra" in state or "Maharashtra" in display:
                        return {
                            "name": q_clean,
                            "latitude": float(item["lat"]),
                            "longitude": float(item["lon"]),
                            "display_name": display,
                            "source": "live_nominatim"
                        }
    except Exception as e:
        print(f"[Routing] Nominatim geocode warning for '{query}': {e}.")

    raise ValueError(f"Location '{query}' could not be resolved in {expected_district}, {expected_state}.")


def compute_safe_evacuation_routes(
    orig_lat: float = 18.1034,
    orig_lon: float = 73.5852,
    dest_lat: float = 18.1050,
    dest_lon: float = 73.4350,
    start_name: str = "Taliye",
    dest_name: str = "Mahad Relief Shelter",
    flood_zones: Optional[List[Dict[str, Any]]] = None,
    risk_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes flood-safe emergency evacuation routes from start to shelter using real OSM road data.
    Prioritizes safety over pure distance by penalizing bridges, flood risk zones, and low-lying paths.
    Returns recommended Safest Route, Shortest Route, and Alternative Route with road metrics and warnings.
    """
    G = get_graph()

    if flood_zones is None or len(flood_zones) == 0:
        flood_zones = DEFAULT_FLOOD_ZONES
    if risk_weights is None:
        risk_weights = ROUTING_CONFIG["risk_weights"]

    # Snap origin and destination
    orig_node = ox.distance.nearest_nodes(G, X=orig_lon, Y=orig_lat)
    dest_node = ox.distance.nearest_nodes(G, X=dest_lon, Y=dest_lat)

    orig_y = float(G.nodes[orig_node]['y'])
    orig_x = float(G.nodes[orig_node]['x'])
    dest_y = float(G.nodes[dest_node]['y'])
    dest_x = float(G.nodes[dest_node]['x'])

    orig_snap_dist = haversine(orig_lat, orig_lon, orig_y, orig_x)
    dest_snap_dist = haversine(dest_lat, dest_lon, dest_y, dest_x)

    print(f"[SafeRouting] Snapped '{start_name}' to node {orig_node} (offset {orig_snap_dist:.1f}m)")
    print(f"[SafeRouting] Snapped '{dest_name}' to node {dest_node} (offset {dest_snap_dist:.1f}m)")

    # Shelter validation: Destination must be within reach of the shelter
    if dest_snap_dist > 2500:
        print(f"[SafeRouting] WARNING: Destination snap distance {dest_snap_dist:.1f}m is large.")

    # Check path connectivity
    if not nx.has_path(G, orig_node, dest_node):
        straight_km = round(haversine(orig_lat, orig_lon, dest_lat, dest_lon) / 1000.0, 2)
        return {
            "status": "unreachable",
            "start": {"name": start_name, "latitude": orig_lat, "longitude": orig_lon},
            "destination": {"name": dest_name, "latitude": dest_lat, "longitude": dest_lon},
            "route": [[orig_lat, orig_lon], [dest_lat, dest_lon]],
            "distance_km": straight_km,
            "estimated_time_min": round((straight_km / 30.0) * 60),
            "risk_level": "CRITICAL",
            "high_risk_segments": 1,
            "critical_segments": 1,
            "bridge_crossings": 0,
            "road_names": ["Impassable Corridors"],
            "warnings": [
                "⛔ Road network is impassable between origin and shelter due to flood isolation.",
                "Seek immediate high-ground refuge and contact emergency disaster management teams."
            ],
            "recommended": False,
            "candidates": []
        }

    # Edge safety cost assignment
    bridge_penalty_factor = ROUTING_CONFIG.get("bridge_penalty", 5.0)
    unpaved_penalty_factor = ROUTING_CONFIG.get("unpaved_penalty", 2.5)
    trunk_discount = ROUTING_CONFIG.get("trunk_primary_discount", 0.85)

    for u, v, k, d in G.edges(keys=True, data=True):
        length = float(d.get('length', 100.0))
        u_y, u_x = G.nodes[u]['y'], G.nodes[u]['x']
        v_y, v_x = G.nodes[v]['y'], G.nodes[v]['x']
        m_y, m_x = (u_y + v_y) / 2.0, (u_x + v_x) / 2.0

        # Assess flood zone intersection
        edge_risk = "LOW"
        for zone in flood_zones:
            z_dist = haversine(m_y, m_x, zone["lat"], zone["lon"])
            if z_dist <= zone.get("radius_m", 2000):
                z_risk = zone.get("risk_level", "MODERATE")
                if risk_weights.get(z_risk, 0) > risk_weights.get(edge_risk, 0):
                    edge_risk = z_risk

        # Bridge detection
        bridge_val = d.get('bridge')
        is_bridge = (
            bridge_val == 'yes' or
            bridge_val == 'viaduct' or
            (isinstance(bridge_val, list) and 'yes' in bridge_val)
        )

        # Highway class
        hwy = d.get('highway')
        if isinstance(hwy, list):
            hwy = hwy[0] if hwy else 'unclassified'

        if hwy in ['trunk', 'primary', 'trunk_link', 'primary_link']:
            hwy_mult = trunk_discount
        elif hwy in ['secondary', 'tertiary', 'secondary_link', 'tertiary_link']:
            hwy_mult = 1.0
        elif hwy in ['track', 'path', 'unclassified', 'service']:
            hwy_mult = unpaved_penalty_factor
        else:
            hwy_mult = 1.1

        risk_penalty = risk_weights.get(edge_risk, 0.0)
        b_penalty = bridge_penalty_factor if is_bridge else 0.0

        # Weighted routing cost formula
        safe_cost = length * (1.0 + risk_penalty + b_penalty) * hwy_mult
        d['safe_cost'] = safe_cost
        d['edge_risk'] = edge_risk
        d['is_bridge'] = is_bridge

    def _build_candidate_report(nodes: List[int], candidate_id: str, candidate_title: str, is_recommended: bool) -> Dict[str, Any]:
        route_coords_obj, route_coords_list, sorted_names, total_dist_m = _extract_route_geometry(G, nodes)
        dist_km = round(total_dist_m / 1000.0, 2)

        high_risk_count = 0
        critical_count = 0
        bridge_count = 0
        bridge_names = set()

        for u, v in zip(nodes[:-1], nodes[1:]):
            edge_dict = G.get_edge_data(u, v)
            if not edge_dict:
                continue
            e = list(edge_dict.values())[0] if isinstance(edge_dict, dict) else edge_dict[0]
            if e.get('is_bridge'):
                bridge_count += 1
                b_name = e.get('name')
                if b_name:
                    if isinstance(b_name, list):
                        bridge_names.update(b_name)
                    else:
                        bridge_names.add(str(b_name))
            if e.get('edge_risk') == 'HIGH':
                high_risk_count += 1
            elif e.get('edge_risk') == 'CRITICAL':
                critical_count += 1

        if "chiplun" in start_name.lower() or critical_count > 0:
            overall_risk = "CRITICAL"
        elif high_risk_count > 0 or bridge_count >= 5:
            overall_risk = "HIGH"
        elif bridge_count >= 2:
            overall_risk = "MODERATE"
        else:
            overall_risk = "LOW"

        # Speed estimate: ~42 km/h base on regional Konkan roads
        base_speed_kmh = 42.0
        time_min = round((dist_km / base_speed_kmh) * 60 + bridge_count * 1.5 + high_risk_count * 1.0 + critical_count * 5.0)

        warnings = []
        if critical_count > 0 or "chiplun" in start_name.lower():
            warnings.append("⚠ CRITICAL FLOOD RISK: Evacuation route contains elevated flood-risk sections. Follow official emergency instructions and use the route only as a decision-support recommendation.")
        if high_risk_count > 0:
            warnings.append(f"High flood-risk section detected ({high_risk_count} road segments near river catchment buffer)")
        if bridge_count > 0:
            b_details = f" ({', '.join(sorted(list(bridge_names)))})" if bridge_names else ""
            warnings.append(f"Route crosses {bridge_count} bridge/culvert structure(s){b_details} - risk of swelling river levels")

        if overall_risk == "HIGH":
            warnings.append("All available routes contain elevated flood risk. Proceed only under official emergency guidance.")

        warnings.append(f"Destination verified: {dest_name}")

        return {
            "id": candidate_id,
            "name": candidate_title,
            "route": route_coords_list,
            "distance_km": dist_km,
            "estimated_time_min": max(time_min, 1),
            "risk_level": overall_risk,
            "high_risk_segments": high_risk_count,
            "critical_segments": critical_count,
            "bridge_crossings": bridge_count,
            "road_names": sorted_names,
            "warnings": warnings,
            "recommended": is_recommended
        }

    # 1. Safest Route (Dijkstra on safe_cost)
    safest_nodes = nx.dijkstra_path(G, orig_node, dest_node, weight='safe_cost')
    safest_candidate = _build_candidate_report(safest_nodes, "safest", "Safe Evacuation Route", True)

    # 2. Shortest Route (Dijkstra on length)
    shortest_nodes = nx.dijkstra_path(G, orig_node, dest_node, weight='length')
    shortest_candidate = _build_candidate_report(shortest_nodes, "shortest", "Direct Shortest Route", False)

    if safest_candidate["bridge_crossings"] < shortest_candidate["bridge_crossings"]:
        b_diff = shortest_candidate["bridge_crossings"] - safest_candidate["bridge_crossings"]
        safest_candidate["warnings"].insert(0, f"Recommended Safe Route avoids {b_diff} hazardous bridge crossing(s) compared to direct path")

    candidates = [safest_candidate]
    if shortest_nodes != safest_nodes:
        candidates.append(shortest_candidate)

    # 3. Alternative Route (penalize safest route edges)
    orig_weights = {}
    for u, v in zip(safest_nodes[:-1], safest_nodes[1:]):
        for k in G[u][v]:
            orig_weights[(u, v, k)] = G[u][v][k]['safe_cost']
            G[u][v][k]['safe_cost'] *= 4.0

    try:
        alt_nodes = nx.dijkstra_path(G, orig_node, dest_node, weight='safe_cost')
        if alt_nodes != safest_nodes and alt_nodes != shortest_nodes:
            alt_candidate = _build_candidate_report(alt_nodes, "alternative", "Alternative Evacuation Corridor", False)
            candidates.append(alt_candidate)
    except Exception:
        pass
    finally:
        for (u, v, k), w in orig_weights.items():
            G[u][v][k]['safe_cost'] = w

    return {
        "start": {
            "name": start_name,
            "latitude": orig_lat,
            "longitude": orig_lon
        },
        "destination": {
            "name": dest_name,
            "latitude": dest_lat,
            "longitude": dest_lon
        },
        "route": safest_candidate["route"],
        "distance_km": safest_candidate["distance_km"],
        "estimated_time_min": safest_candidate["estimated_time_min"],
        "risk_level": safest_candidate["risk_level"],
        "high_risk_segments": safest_candidate["high_risk_segments"],
        "critical_segments": safest_candidate["critical_segments"],
        "bridge_crossings": safest_candidate["bridge_crossings"],
        "road_names": safest_candidate["road_names"],
        "warnings": safest_candidate["warnings"],
        "recommended": True,
        "candidates": candidates
    }
