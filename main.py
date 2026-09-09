import math
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Konkan Flash-Flood Early Warning System (SIH 26192)",
    description="Flash-flood risk prediction and early warning monitoring for Konkan region villages",
    version="1.0.0",
)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from data_loader import data_loader

# Dynamically populated monitoring registry from data_loader
VILLAGE_DATA = {v["village_id"]: v for v in data_loader.get_villages_list()}


# Request & Response Schemas
class PredictRiskRequest(BaseModel):
    village_id: Optional[str] = Field(None, description="Unique village identifier, e.g., 'chiplun'")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lon: Optional[float] = Field(None, description="Longitude coordinate")
    rainfall_24h_mm: Optional[float] = Field(None, description="Optional current rainfall override")


class PredictRiskResponse(BaseModel):
    village_id: str
    probability: float
    risk: str  # "LOW", "MODERATE", "HIGH", "CRITICAL"
    estimated_warning_window_min: int
    confidence: float


class NextAffectedVillage(BaseModel):
    name: str
    concern_level: str  # "Elevated" | "Watch" | "Low"
    distance_km: float
    factors_considered: list[str]
    unavailable_factors: list[str]


class RiskPropagationResponse(BaseModel):
    source_village: dict
    estimated_next_affected: list[NextAffectedVillage]
    note: str


@app.get("/api/villages")
def get_monitored_villages():
    """
    Returns dynamic list of all monitored villages with high-precision coordinates
    and terrain metrics loaded directly from village_terrain_summary.csv.
    """
    return data_loader.get_villages_list()


@app.get("/api/shelters")
def get_designated_shelters():
    """
    Returns dynamic list of all designated emergency relief shelters.
    """
    return data_loader.get_shelters_list()


@app.get("/api/villages/all-risks")
def get_all_villages_risk():
    """
    Returns dynamic risk evaluations for all villages from dataset telemetry,
    sorted by risk probability descending.
    """
    return data_loader.get_all_villages_risk()


@app.post("/predict-risk", response_model=PredictRiskResponse)
def predict_risk(payload: PredictRiskRequest):
    """
    Predict flash-flood risk at village level in the Konkan region.
    Accepts village_id, lat, and lon, returning probability, risk category,
    estimated warning window in minutes, and model confidence score dynamically
    computed from rainfall_risk_features_updated.csv and village_terrain_summary.csv.
    """
    res = data_loader.evaluate_village_risk(
        village_id=payload.village_id,
        lat=payload.lat,
        lon=payload.lon,
        custom_rainfall_mm=payload.rainfall_24h_mm
    )

    return PredictRiskResponse(
        village_id=payload.village_id or res["village_id"],
        probability=res["probability"],
        risk=res["risk"],
        estimated_warning_window_min=res["estimated_warning_window_min"],
        confidence=res["confidence"],
    )


@app.get("/api/risk/propagation/{location_id}", response_model=RiskPropagationResponse)
def get_downstream_risk_propagation(location_id: str):
    """
    Estimated Downstream Risk Propagation (Spatial & Hydrological Heuristic).
    Provides situational awareness ranking for neighboring villages when a source village is at risk,
    evaluating terrain elevation differences, slope, and river basin connectivity.
    """
    prop = data_loader.evaluate_risk_propagation(location_id)
    if not prop:
        raise HTTPException(status_code=404, detail=f"Village '{location_id}' not found in monitoring registry.")

    return RiskPropagationResponse(
        source_village={
            "village_id": prop["source_village"]["village_id"],
            "name": prop["source_village"]["name"],
            "current_risk": prop["source_village"]["current_risk"],
        },
        estimated_next_affected=[
            NextAffectedVillage(
                name=c["name"],
                concern_level=c["concern_level"],
                distance_km=c["distance_km"],
                factors_considered=c["factors_considered"],
                unavailable_factors=c["unavailable_factors"],
            )
            for c in prop["estimated_next_affected"]
        ],
        note=prop["note"],
    )

from routing import (
    compute_dijkstra_evacuation_route,
    compute_multi_origin_routes,
    compute_safe_evacuation_routes,
    geocode_location,
    ORIGIN_LOCALITIES,
    DESIGNATED_SHELTERS
)

# Request & Response Schemas
class LatLngPoint(BaseModel):
    lat: float
    lng: float

class EvacuationRouteRequest(BaseModel):
    origin: LatLngPoint
    destination: LatLngPoint
    weight: Optional[str] = "length"

class EvacuationRouteResponse(BaseModel):
    status: str
    origin_snapped: LatLngPoint
    destination_snapped: LatLngPoint
    straight_distance_km: float
    distance_km: float
    nodes_count: int
    geometry_count: int
    road_names: list[str]
    route: list[LatLngPoint]
    coordinates: list[list[float]]

class OriginPoint(BaseModel):
    name: str
    lat: float
    lng: Optional[float] = None
    lon: Optional[float] = None

class MultiEvacuationRouteRequest(BaseModel):
    destination: LatLngPoint
    origins: Optional[list[OriginPoint]] = None
    weight: Optional[str] = "length"

class SingleOriginRouteResult(BaseModel):
    origin_name: str
    status: str
    origin_snapped: LatLngPoint
    destination_snapped: LatLngPoint
    straight_distance_km: float
    distance_km: float
    nodes_count: int
    geometry_count: int
    road_names: list[str]
    route: list[LatLngPoint]
    coordinates: list[list[float]]

class MultiEvacuationRouteResponse(BaseModel):
    routes: list[SingleOriginRouteResult]


@app.post("/api/routes/evacuation", response_model=EvacuationRouteResponse)
@app.post("/evacuation-route", response_model=EvacuationRouteResponse)
def get_evacuation_route(payload: EvacuationRouteRequest):
    """
    Computes a real road evacuation route using Dijkstra's algorithm on an OSM drivable graph.
    Accepts origin and destination coordinates, returning full street curve geometry and road statistics.
    """
    res = compute_dijkstra_evacuation_route(
        orig_lat=payload.origin.lat,
        orig_lon=payload.origin.lng,
        dest_lat=payload.destination.lat,
        dest_lon=payload.destination.lng,
        weight_param=payload.weight or "length"
    )
    return res


@app.post("/api/routes/evacuation/multi", response_model=MultiEvacuationRouteResponse)
def get_multi_evacuation_routes(payload: MultiEvacuationRouteRequest):
    """
    Computes multiple evacuation routes from several origin points (localities/wards)
    to a single destination shelter using a single reversed Dijkstra pathfinding computation.
    If origins is omitted or empty, defaults to predefined ORIGIN_LOCALITIES.
    """
    origins_list = None
    if payload.origins:
        origins_list = [
            {
                "name": orig.name,
                "lat": orig.lat,
                "lon": orig.lon if orig.lon is not None else (orig.lng if orig.lng is not None else 0.0)
            }
            for orig in payload.origins
        ]

    routes = compute_multi_origin_routes(
        origins=origins_list,
        dest_lat=payload.destination.lat,
        dest_lon=payload.destination.lng,
        weight_param=payload.weight or "length"
    )
    return {"routes": routes}


# Safe Evacuation Route Models
class LocationPoint(BaseModel):
    name: str
    latitude: float
    longitude: float


class CandidateRoute(BaseModel):
    id: str
    name: str
    route: list[list[float]]
    distance_km: float
    estimated_time_min: int
    risk_level: str
    high_risk_segments: int
    critical_segments: int
    bridge_crossings: int
    road_names: list[str]
    warnings: list[str]
    recommended: bool


class SafeEvacuationRouteResponse(BaseModel):
    start: LocationPoint
    destination: LocationPoint
    route: list[list[float]]
    distance_km: float
    estimated_time_min: int
    risk_level: str
    high_risk_segments: int
    critical_segments: int
    bridge_crossings: int
    road_names: list[str]
    warnings: list[str]
    recommended: bool
    candidates: list[CandidateRoute]


@app.get("/api/evacuation-route", response_model=SafeEvacuationRouteResponse)
@app.get("/evacuation-route-safe", response_model=SafeEvacuationRouteResponse)
def get_safe_flood_evacuation_route(
    start: str = "Mahad",
    destination: Optional[str] = None,
    weight: Optional[str] = "safety"
):
    """
    Computes a real-world safe flood evacuation route using OSM road network data.
    Prioritizes safety over shortest distance: penalizes river crossings, low-lying zones,
    and road segments inside flood risk buffers.
    Supports both Chiplun -> Chiplun Shelter and Mahad -> Mahad Shelter.
    """
    start_clean = start.strip()
    start_lower = start_clean.lower()

    # 1. Determine expected districts and default destination
    if "chiplun" in start_lower:
        start_district = "Ratnagiri"
        default_dest = "Chiplun Shelter"
    else:
        start_district = "Raigad"
        default_dest = "Mahad Relief Shelter"

    # Resolve start location
    try:
        start_loc = geocode_location(start_clean, expected_district=start_district, expected_state="Maharashtra")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding service error for '{start}': {str(e)}")

    # 2. Resolve destination location (prioritizing shelter validation)
    dest_query = (destination or default_dest).strip()
    dest_lower = dest_query.lower()
    if "shelter" not in dest_lower and "camp" not in dest_lower:
        if "chiplun" in dest_lower:
            dest_query = "Chiplun Shelter"
        elif "mahad" in dest_lower:
            dest_query = "Mahad Relief Shelter"

    dest_district = "Ratnagiri" if "chiplun" in dest_query.lower() else "Raigad"

    try:
        dest_loc = geocode_location(dest_query, expected_district=dest_district, expected_state="Maharashtra")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding service error for '{dest_query}': {str(e)}")

    # 3. Assemble active flood zones from currently monitored villages
    active_flood_zones = []
    for vrisk in data_loader.get_all_villages_risk():
        r_level = vrisk["risk"]
        active_flood_zones.append({
            "name": vrisk["village_name"],
            "lat": vrisk["lat"],
            "lon": vrisk["lon"],
            "radius_m": 2500 if r_level in ["HIGH", "CRITICAL"] else 1800,
            "risk_level": r_level
        })

    # Add specific Savitri river corridor buffer near Mahad
    active_flood_zones.append({
        "name": "Savitri Low-Lying River Corridor",
        "lat": 18.0950,
        "lon": 73.4600,
        "radius_m": 2000,
        "risk_level": "HIGH"
    })

    # Add specific Vashishti river corridor buffer near Chiplun
    active_flood_zones.append({
        "name": "Vashishti River Flood Corridor",
        "lat": 17.5350,
        "lon": 73.5250,
        "radius_m": 2200,
        "risk_level": "CRITICAL"
    })

    try:
        result = compute_safe_evacuation_routes(
            orig_lat=start_loc["latitude"],
            orig_lon=start_loc["longitude"],
            dest_lat=dest_loc["latitude"],
            dest_lon=dest_loc["longitude"],
            start_name=start_loc["name"],
            dest_name=dest_loc["name"],
            flood_zones=active_flood_zones
        )
        return result
    except Exception as e:
        print(f"[API] Evacuation routing error: {e}")
        raise HTTPException(status_code=500, detail=f"Route calculation failed: {str(e)}")



# Static Files & React Frontend Hosting
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")

if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve React frontend single-page application and static resources.
    Falls back to static/index.html for client-side routing.
    """
    if full_path:
        candidate = os.path.join(STATIC_DIR, full_path)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return FileResponse(candidate)

    index_html = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_html):
        return FileResponse(index_html)

    return {
        "status": "online",
        "message": "Konkan Flash-Flood Early Warning API is running. Build frontend into /static to view dashboard.",
        "api_docs": "/docs",
        "predict_risk_endpoint": "POST /predict-risk",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
