// Predefined Konkan Region Villages for SIH Problem Statement 26192
export const VILLAGES = [
  {
    village_id: "chiplun",
    name: "Chiplun",
    district: "Ratnagiri",
    river_basin: "Vashishti River",
    lat: 17.5323,
    lon: 73.5177,
  },
  {
    village_id: "mahad",
    name: "Mahad",
    district: "Raigad",
    river_basin: "Savitri River",
    lat: 18.0827,
    lon: 73.4188,
  },
  {
    village_id: "taliye",
    name: "Taliye",
    district: "Raigad",
    river_basin: "Savitri Catchment",
    lat: 18.1034,
    lon: 73.5852,
  },
  {
    village_id: "poladpur",
    name: "Poladpur",
    district: "Raigad",
    river_basin: "Savitri-Amba Confluence",
    lat: 17.9806,
    lon: 73.4664,
  },
  {
    village_id: "khed",
    name: "Khed",
    district: "Ratnagiri",
    river_basin: "Jagbudi River",
    lat: 17.7214,
    lon: 73.3905,
  },
  {
    village_id: "dapoli",
    name: "Dapoli",
    district: "Ratnagiri",
    river_basin: "Jog River Basin",
    lat: 17.7621,
    lon: 73.1856,
  },
  {
    village_id: "guhagar",
    name: "Guhagar",
    district: "Ratnagiri",
    river_basin: "Coastal Drainage",
    lat: 17.4855,
    lon: 73.1934,
  },
];

// Hardcoded Emergency Evacuation Shelters
export const SHELTERS = [
  {
    id: "shelter-chiplun",
    name: "Chiplun Relief Shelter",
    lat: 17.5580,
    lon: 73.5420,
    capacity: "1,200 Persons",
    type: "Elevated Disaster Shelter",
  },
  {
    id: "shelter-mahad",
    name: "Mahad Civil Defence Shelter",
    lat: 18.1050,
    lon: 73.4350,
    capacity: "1,500 Persons",
    type: "Multi-Purpose Cyclone & Flood Shelter",
  },
  {
    id: "shelter-guhagar",
    name: "Guhagar Coastal Multi-Purpose Shelter",
    lat: 17.4980,
    lon: 73.2100,
    capacity: "800 Persons",
    type: "High-Elevation Community Center",
  },
];

// Color and radius mapping per specification:
// LOW -> Green (3000m), MODERATE -> Yellow (4000m), HIGH -> Orange (5500m), CRITICAL -> Red (7000m)
// Note: Radius values (in meters) are illustrative for the prototype/demo, not derived from actual flood-extent modeling.
export const RISK_COLORS = {
  LOW: {
    badge: "#16a34a",
    bg: "#dcfce7",
    border: "#86efac",
    text: "#15803d",
    fill: "#22c55e",
    label: "LOW RISK",
    radius: 3000,
  },
  MODERATE: {
    badge: "#ca8a04",
    bg: "#fef9c3",
    border: "#fde047",
    text: "#854d0e",
    fill: "#eab308",
    label: "MODERATE RISK",
    radius: 4000,
  },
  HIGH: {
    badge: "#ea580c",
    bg: "#ffedd5",
    border: "#fdba74",
    text: "#9a3412",
    fill: "#f97316",
    label: "HIGH RISK",
    radius: 5500,
  },
  CRITICAL: {
    badge: "#dc2626",
    bg: "#fee2e2",
    border: "#fca5a5",
    text: "#991b1b",
    fill: "#ef4444",
    label: "CRITICAL RISK",
    radius: 7000,
  },
};

// Helper: Calculate simple Euclidean or Haversine distance
export function findNearestShelter(lat, lon, shelterList = SHELTERS) {
  let nearest = null;
  let minDistance = Infinity;

  shelterList.forEach((shelter) => {
    const dLat = shelter.lat - lat;
    const dLon = shelter.lon - lon;
    const dist = Math.sqrt(dLat * dLat + dLon * dLon);
    if (dist < minDistance) {
      minDistance = dist;
      nearest = shelter;
    }
  });

  return nearest;
}
