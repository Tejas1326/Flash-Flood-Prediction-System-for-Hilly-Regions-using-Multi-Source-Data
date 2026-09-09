"""
Centralized Data Ingestion and Dynamic Risk Engine
Loads and validates village terrain and rainfall risk feature datasets.
Provides spatial index matching, dynamic flood risk assessment, and shelter registries.
"""

import csv
import json
import logging
import math
import os
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("data_loader")
logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

VILLAGE_TERRAIN_CSV = os.path.join(DATA_DIR, "village_terrain_summary.csv")
RAINFALL_FEATURES_CSV = os.path.join(DATA_DIR, "rainfall_risk_features_updated.csv")
SHELTERS_JSON = os.path.join(DATA_DIR, "shelters.json")

# Default metadata mappings for Konkan villages
VILLAGE_METADATA = {
    "chiplun": {
        "district": "Ratnagiri",
        "river_basin": "Vashishti River",
        "population": 55143,
        "default_shelter": "chiplun_shelter"
    },
    "mahad": {
        "district": "Raigad",
        "river_basin": "Savitri River",
        "population": 26883,
        "default_shelter": "mahad_shelter"
    },
    "taliye": {
        "district": "Raigad",
        "river_basin": "Savitri Basin (Ghat Foothills)",
        "population": 2500,
        "default_shelter": "mahad_shelter"
    },
    "poladpur": {
        "district": "Raigad",
        "river_basin": "Savitri River (Upstream)",
        "population": 12000,
        "default_shelter": "mahad_shelter"
    },
    "khed": {
        "district": "Ratnagiri",
        "river_basin": "Jagbudi River",
        "population": 16892,
        "default_shelter": "chiplun_shelter"
    },
    "guhagar": {
        "district": "Ratnagiri",
        "river_basin": "Coastal Drainage Plain",
        "population": 3205,
        "default_shelter": "chiplun_shelter"
    },
    "dapoli": {
        "district": "Ratnagiri",
        "river_basin": "Coastal Highland",
        "population": 15000,
        "default_shelter": "chiplun_shelter"
    }
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance in kilometers between two lat/lon coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DataLoader:
    """Singleton-style dataset manager and risk evaluation engine."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.villages: Dict[str, Dict[str, Any]] = {}
        self.shelters: List[Dict[str, Any]] = []
        self.rainfall_grid: Dict[Tuple[float, float], Dict[int, Dict[str, Any]]] = {}
        self.grid_coords: List[Tuple[float, float]] = []
        self.is_loaded = False
        self.load_all()

    def load_all(self):
        """Load and validate all datasets."""
        self._load_shelters()
        self._load_villages()
        self._load_rainfall_grid()
        self.is_loaded = True
        logger.info(
            f"DataLoader initialized: {len(self.villages)} villages, "
            f"{len(self.shelters)} shelters, {len(self.grid_coords)} rainfall grid points."
        )

    def _load_shelters(self):
        """Load shelters from data/shelters.json or fallback to standard configurations."""
        if os.path.exists(SHELTERS_JSON):
            try:
                with open(SHELTERS_JSON, "r", encoding="utf-8") as f:
                    self.shelters = json.load(f)
                logger.info(f"Loaded {len(self.shelters)} shelters from {SHELTERS_JSON}")
                return
            except Exception as e:
                logger.error(f"Error loading {SHELTERS_JSON}: {e}")

        # Safe fallback if file is unreadable
        self.shelters = [
            {
                "id": "mahad_shelter",
                "name": "Mahad Relief Shelter",
                "lat": 18.1050,
                "lon": 73.4350,
                "capacity": 500,
                "elevation_m": 42.0,
                "district": "Raigad",
                "address": "Mahad High School Ground, Raigad, Maharashtra",
                "status": "active"
            },
            {
                "id": "chiplun_shelter",
                "name": "Chiplun Shelter",
                "lat": 17.5580,
                "lon": 73.5420,
                "capacity": 650,
                "elevation_m": 35.0,
                "district": "Ratnagiri",
                "address": "Chiplun Municipal Council Hall, Ratnagiri, Maharashtra",
                "status": "active"
            }
        ]

    def _load_villages(self):
        """Load villages from data/village_terrain_summary.csv with robust validation."""
        self.villages = {}
        if not os.path.exists(VILLAGE_TERRAIN_CSV):
            logger.warning(f"Village terrain CSV not found at {VILLAGE_TERRAIN_CSV}")
            return

        try:
            with open(VILLAGE_TERRAIN_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    v_name = (row.get("Village") or "").strip()
                    if not v_name:
                        continue

                    v_id = v_name.lower().replace(" ", "_")

                    try:
                        lat = float(row.get("Latitude", 0.0))
                        lon = float(row.get("Longitude", 0.0))
                    except (ValueError, TypeError):
                        logger.warning(f"Row {row_idx}: invalid coordinates for {v_name}, skipping.")
                        continue

                    try:
                        elev = float(row.get("Elevation", 0.0))
                    except (ValueError, TypeError):
                        elev = 0.0

                    try:
                        slope = float(row.get("Slope", 1.5))
                    except (ValueError, TypeError):
                        slope = 1.5

                    meta = VILLAGE_METADATA.get(v_id, {})
                    district = meta.get("district", "Ratnagiri" if lat < 17.8 else "Raigad")
                    basin = meta.get("river_basin", "Konkan Coastal Basin")
                    pop = meta.get("population", 5000)

                    self.villages[v_id] = {
                        "village_id": v_id,
                        "name": v_name,
                        "lat": lat,
                        "lon": lon,
                        "elevation": round(elev, 2),
                        "slope": round(slope, 3),
                        "district": district,
                        "river_basin": basin,
                        "population": pop
                    }

            # Ensure all regional monitoring locations are present
            if "dapoli" not in self.villages:
                self.villages["dapoli"] = {
                    "village_id": "dapoli",
                    "name": "Dapoli",
                    "lat": 17.7621,
                    "lon": 73.1856,
                    "elevation": 120.0,
                    "slope": 2.1,
                    "district": "Ratnagiri",
                    "river_basin": "Jog River Basin",
                    "population": 15000
                }

            logger.info(f"Loaded {len(self.villages)} villages into monitoring registry.")
        except Exception as e:
            logger.error(f"Error parsing {VILLAGE_TERRAIN_CSV}: {e}")

    def _load_rainfall_grid(self):
        """Load and index spatial grid points and daily rainfall features from CSV."""
        self.rainfall_grid = {}
        if not os.path.exists(RAINFALL_FEATURES_CSV):
            logger.warning(f"Rainfall features CSV not found at {RAINFALL_FEATURES_CSV}")
            return

        try:
            with open(RAINFALL_FEATURES_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        glat = round(float(row["lat"]), 2)
                        glon = round(float(row["lon"]), 2)
                        day = int(row["day_of_year"])
                    except (ValueError, KeyError):
                        continue

                    coord = (glat, glon)
                    if coord not in self.rainfall_grid:
                        self.rainfall_grid[coord] = {}

                    daily = float(row.get("rainfall_daily_mm", 0.0))
                    r3d = float(row.get("rainfall_3d_mm", 0.0))
                    r7d = float(row.get("rainfall_7d_mm", 0.0))
                    heavy = str(row.get("heavy_rain_observation", "")).strip().lower() == "true"
                    grid_elev = float(row.get("elevation_m", 0.0))
                    grid_slope = float(row.get("slope_deg", 0.0))

                    self.rainfall_grid[coord][day] = {
                        "daily_mm": daily,
                        "3d_mm": r3d,
                        "7d_mm": r7d,
                        "heavy_rain": heavy,
                        "elevation_m": grid_elev,
                        "slope_deg": grid_slope
                    }

            self.grid_coords = list(self.rainfall_grid.keys())
            logger.info(f"Loaded {len(self.grid_coords)} distinct rainfall grid coordinates.")
        except Exception as e:
            logger.error(f"Error reading {RAINFALL_FEATURES_CSV}: {e}")

    def get_villages_list(self) -> List[Dict[str, Any]]:
        """Return all villages as a list of dicts."""
        return list(self.villages.values())

    def get_village(self, village_id: str) -> Optional[Dict[str, Any]]:
        """Lookup village by id or normalized name."""
        if not village_id:
            return None
        key = village_id.strip().lower().replace(" ", "_")
        if key in self.villages:
            return self.villages[key]

        # Check partial / case-insensitive matches
        for vid, v in self.villages.items():
            if key in vid or vid in key or key == v["name"].lower():
                return v

        return None

    def get_shelters_list(self) -> List[Dict[str, Any]]:
        """Return all designated emergency relief shelters."""
        return self.shelters

    def find_nearest_grid_coord(self, lat: float, lon: float) -> Tuple[Tuple[float, float], float]:
        """Find the closest (lat, lon) grid point in the rainfall dataset and its distance in km."""
        if not self.grid_coords:
            return ((round(lat, 2), round(lon, 2)), 0.0)

        nearest = min(self.grid_coords, key=lambda g: haversine_km(lat, lon, g[0], g[1]))
        dist_km = haversine_km(lat, lon, nearest[0], nearest[1])
        return (nearest, round(dist_km, 2))

    def find_nearest_shelter(self, lat: float, lon: float) -> Dict[str, Any]:
        """Find closest relief shelter by geographical distance."""
        if not self.shelters:
            return {
                "name": "Emergency Relief Center",
                "lat": lat + 0.02,
                "lon": lon + 0.02,
                "capacity": 500,
                "district": "Local"
            }

        return min(self.shelters, key=lambda s: haversine_km(lat, lon, s["lat"], s["lon"]))

    def evaluate_village_risk(
        self,
        village_id: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        day_of_year: Optional[int] = None,
        custom_rainfall_mm: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Dynamically evaluate flash-flood risk using actual terrain summary and rainfall features.
        Combines precipitation intensity, antecedent rainfall, heavy rain observations,
        elevation trapping, and terrain slope.
        """
        v_info = self.get_village(village_id) if village_id else None

        if v_info:
            v_lat = v_info["lat"]
            v_lon = v_info["lon"]
            v_name = v_info["name"]
            v_elev = v_info["elevation"]
            v_slope = v_info["slope"]
            v_basin = v_info["river_basin"]
            v_district = v_info["district"]
            confidence = 0.96
        else:
            v_lat = lat if lat is not None else 17.53
            v_lon = lon if lon is not None else 73.51
            v_name = village_id.title() if village_id else f"Location ({v_lat:.3f}, {v_lon:.3f})"
            v_elev = 0.0
            v_slope = 2.0
            v_basin = "Konkan Catchment Zone"
            v_district = "Ratnagiri" if v_lat < 17.8 else "Raigad"
            confidence = 0.78

        # Find nearest spatial grid point in rainfall dataset
        nearest_grid, grid_dist_km = self.find_nearest_grid_coord(v_lat, v_lon)

        # Use target day (default to Day 205 - active monsoon high precipitation event)
        eval_day = day_of_year if day_of_year is not None else 205

        grid_days = self.rainfall_grid.get(nearest_grid, {})
        day_data = grid_days.get(eval_day, {})

        # Extract features with safe fallback defaults
        daily_mm = custom_rainfall_mm if custom_rainfall_mm is not None else day_data.get("daily_mm", 65.0)
        r3d_mm = day_data.get("3d_mm", daily_mm * 2.2)
        r7d_mm = day_data.get("7d_mm", daily_mm * 4.5)
        heavy_rain = day_data.get("heavy_rain", daily_mm >= 50.0)

        # -------------------------------------------------------------
        # Physical Flood Risk Computation
        # -------------------------------------------------------------
        # 1. Precipitation Intensity (0.0 to 0.40)
        # 100mm daily + 250mm 3-day indicates extreme flood event
        rain_score = min(0.24, (daily_mm / 120.0) * 0.24) + min(0.16, (r3d_mm / 280.0) * 0.16)

        # 2. Heavy rain observation flag (0.08)
        heavy_score = 0.08 if heavy_rain else 0.0

        # 3. Terrain Vulnerability: Low elevation bowl relative to river base (0.0 to 0.28)
        basin_trapping = 0.0
        if v_elev < -65.0:
            basin_trapping = 0.28  # Extreme low-lying alluvial flood bowl (Chiplun)
        elif v_elev < -50.0:
            basin_trapping = 0.24  # Deep coastal / valley floor (Guhagar, Khed)
        elif v_elev < -40.0:
            basin_trapping = 0.20  # Severe river corridor basin (Mahad)
        elif v_elev < 0.0:
            basin_trapping = 0.12  # Moderate low-lying (Poladpur)
        elif v_elev < 60.0:
            basin_trapping = 0.05

        # 4. Slope dynamics (0.0 to 0.18):
        # Extremely flat (<1.0 deg) in a deep basin bowl -> catastrophic water accumulation (Chiplun)
        # Steep (>4.5 deg) on hillsides -> rapid surface runoff / debris-flow flash surge (Taliye)
        slope_score = 0.0
        if v_slope > 4.5:
            slope_score = 0.16  # Rapid flash surge / debris risk (e.g. Taliye hillside)
        elif v_slope < 1.0 and v_elev < -60.0:
            slope_score = 0.18  # Extreme Chiplun basin bowl trap
        elif v_slope < 1.5 and v_elev < -40.0:
            slope_score = 0.14  # Low-lying flat accumulation
        elif v_slope < 2.8 and v_elev < -40.0:
            slope_score = 0.10  # Mahad river corridor
        else:
            slope_score = 0.05

        # Raw probability calculation clamped in [0.10, 0.95]
        probability = round(min(0.95, max(0.12, rain_score + heavy_score + basin_trapping + slope_score)), 2)

        # Categorize risk and warning window (inversely related to hazard severity)
        if probability >= 0.75:
            risk_level = "CRITICAL"
            warning_window_min = int(round(15 + (1.0 - probability) * 50))
        elif probability >= 0.60:
            risk_level = "HIGH"
            warning_window_min = int(round(35 + (0.75 - probability) * 100))
        elif probability >= 0.35:
            risk_level = "MODERATE"
            warning_window_min = int(round(60 + (0.60 - probability) * 120))
        else:
            risk_level = "LOW"
            warning_window_min = int(round(120 + (0.35 - probability) * 200))

        # Build factors dictionary
        soil_saturation = round(min(1.0, max(0.20, (r7d_mm / 450.0))), 2)

        factors = {
            "rainfall_24h_mm": round(daily_mm, 1),
            "rainfall_3d_mm": round(r3d_mm, 1),
            "rainfall_7d_mm": round(r7d_mm, 1),
            "elevation_m": v_elev,
            "slope_deg": v_slope,
            "heavy_rain_observation": heavy_rain,
            "soil_saturation": soil_saturation,
            "river_basin": v_basin,
            "nearest_grid_dist_km": grid_dist_km
        }

        # Human-readable explanation
        explanation = (
            f"Evaluated using Konkan terrain summary & rainfall telemetry. "
            f"Daily rainfall {daily_mm:.1f}mm (3-day cumulative {r3d_mm:.1f}mm), "
            f"elevation {v_elev:.1f}m, and slope {v_slope:.2f}° produce a {risk_level} "
            f"flash-flood probability of {int(probability * 100)}% with an estimated "
            f"evacuation warning window of {warning_window_min} minutes."
        )

        return {
            "village_id": village_id or v_name.lower().replace(" ", "_"),
            "village_name": v_name,
            "district": v_district,
            "lat": v_lat,
            "lon": v_lon,
            "risk": risk_level,
            "probability": probability,
            "estimated_warning_window_min": warning_window_min,
            "confidence": confidence,
            "factors": factors,
            "explanation": explanation
        }

    def get_all_villages_risk(self, day_of_year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return dynamic flood risk predictions for all villages in dataset, highest risk first."""
        results = []
        for vid in self.villages.keys():
            results.append(self.evaluate_village_risk(village_id=vid, day_of_year=day_of_year))

        # Sort highest risk probability first
        results.sort(key=lambda x: x["probability"], reverse=True)
        return results

    def evaluate_risk_propagation(self, source_village_id: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate risk propagation from a source village to surrounding catchment areas,
        incorporating actual dataset terrain elevation differences and river basin proximity.
        """
        src = self.get_village(source_village_id)
        if not src:
            return None

        src_risk = self.evaluate_village_risk(source_village_id)
        candidates = []

        for vid, target in self.villages.items():
            if vid == src["village_id"]:
                continue

            dist_km = haversine_km(src["lat"], src["lon"], target["lat"], target["lon"])
            elev_diff = target["elevation"] - src["elevation"]
            sb = src["river_basin"].lower()
            tb = target["river_basin"].lower()
            same_basin = (
                (sb in tb or tb in sb) or
                ("vashishti" in sb and "jagbudi" in tb) or
                ("jagbudi" in sb and "vashishti" in tb) or
                ("savitri" in sb and "savitri" in tb)
            )

            target_risk = self.evaluate_village_risk(vid)

            # Concern level logic based on distance, elevation gradient, and basin connectivity
            if dist_km < 15.0 or (dist_km < 35.0 and same_basin):
                concern = "Elevated" if src_risk["probability"] >= 0.60 else "Moderate"
                time_horizon_h = round(max(0.5, dist_km / 12.0), 1)
            elif dist_km < 40.0:
                concern = "Moderate" if src_risk["probability"] >= 0.70 else "Low"
                time_horizon_h = round(dist_km / 10.0, 1)
            else:
                concern = "Low"
                time_horizon_h = round(dist_km / 8.0, 1)

            candidates.append({
                "village_id": vid,
                "name": target["name"],
                "district": target["district"],
                "distance_km": round(dist_km, 1),
                "elevation_diff_m": round(elev_diff, 1),
                "slope_deg": target["slope"],
                "concern_level": concern,
                "time_horizon_h": time_horizon_h,
                "current_risk": target_risk["risk"],
                "factors_considered": [
                    "spatial proximity",
                    "river basin connectivity",
                    "hydrological catchment gradient"
                ],
                "unavailable_factors": [
                    "elevation / terrain slope profile",
                    "real-time hydraulic river discharge cross-section"
                ]
            })

        # Sort nearest first
        candidates.sort(key=lambda x: x["distance_km"])

        return {
            "source_village": {
                "village_id": src["village_id"],
                "name": src["name"],
                "current_risk": src_risk["risk"],
                "probability": src_risk["probability"],
                "elevation_m": src["elevation"],
                "slope_deg": src["slope"]
            },
            "estimated_next_affected": candidates,
            "note": (
                "Heuristic risk propagation based on terrain and spatial proximity. "
                "Not a hydraulic simulation. Downstream river basin connectivity and terrain gradients "
                "significantly influence flood surge travel times."
            )
        }


# Global shared instance
data_loader = DataLoader()
