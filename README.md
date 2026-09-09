# Konkan Region Flash-Flood Early Warning Dashboard (SIH PS 26192)

A fast, single-page flash-flood early warning and emergency routing dashboard demo built for **Smart India Hackathon (SIH) Problem Statement 26192**.

The system predicts flash-flood risk at the village level in the vulnerable **Konkan region of Maharashtra**, provides an interactive **Leaflet.js map**, dynamically assesses risk for 7 key villages using a **Python FastAPI backend**, automatically identifies the highest-risk village to issue an emergency warning alert, and traces the recommended evacuation route to a high-ground disaster shelter.

---

## Quick Start (Single Process)

The entire application runs as a **single integrated FastAPI application** serving both the API and the React frontend.

### 1. Install Backend Dependencies (if needed)

```bash
pip install -r requirements.txt
```

### 2. Start the Server

```bash
uvicorn main:app --reload
```

### 3. Open in Browser

Navigate to:
```
http://127.0.0.1:8000
```

Interactive API documentation is also available at:
```
http://127.0.0.1:8000/docs
```

---

## Key Features

- **Interactive Leaflet Map**:
  - Centered on the Konkan region (`~17.8° N, ~73.4° E`).
  - OpenStreetMap tiles with zero paid/external map keys required.
  - Interactive markers for 7 Konkan villages: **Chiplun**, **Mahad**, **Taliye**, **Poladpur**, **Khed**, **Dapoli**, and **Guhagar**.
- **Dynamic API Risk Prediction (`/predict-risk`)**:
  - When the dashboard loads, the frontend calls the FastAPI `/predict-risk` endpoint once for each village.
  - Returns realistic hydrological risk metrics: `probability`, `risk` (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), `estimated_warning_window_min`, and `confidence`.
  - Markers dynamically update their color coding:
    - 🟢 **LOW**: `< 35%` risk (Green)
    - 🟡 **MODERATE**: `35% – 59%` risk (Yellow)
    - 🟠 **HIGH**: `60% – 79%` risk (Orange)
    - 🔴 **CRITICAL**: `≥ 80%` risk (Red with animated emergency pulse)
- **Village Detail Inspection**:
  - Clicking any village pin displays a Leaflet popup showing the village name, risk classification, probability %, warning window, and model confidence.
  - A summary matrix and inspection card below the map allows quick comparison across all monitored villages.
- **Automated Highest-Risk Warning & Evacuation Routing**:
  - Compares the returned probability scores and flags the highest-risk village (e.g. Chiplun at 88% Critical).
  - Displays the emergency alert banner below the map:
    > **FLASH FLOOD WARNING — Village: Chiplun — Risk: CRITICAL — Potential onset: 25 min — Action: Move to nearest shelter — Recommended route shown on map**
  - Traces a highlighted dashed evacuation polyline on the map directly from the highest-risk village to the nearest designated emergency shelter (**Chiplun High-Ground Relief Camp**).
- **Emergency Relief Shelters**:
  - Hardcoded safe shelters in high-elevation zones (Chiplun High-Ground Relief Camp, Mahad Civil Defence Shelter, Guhagar Coastal Flood Center).

---

## Project Structure

```
SIH-DevKraft/
├── main.py                  # Python FastAPI server (serves /predict-risk & static frontend)
├── requirements.txt         # Python dependencies (fastapi, uvicorn, pydantic)
├── test_system.py           # Automated test suite for endpoints and predictions
├── static/                  # Production build of React frontend (served by FastAPI)
│   ├── index.html
│   └── assets/
│       ├── index-*.js
│       └── index-*.css
└── frontend/                # React source code (Vite)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── index.css
        ├── main.jsx
        ├── components/
        │   ├── Header.jsx
        │   ├── MapView.jsx
        │   ├── WarningAlert.jsx
        │   └── VillageDetailPanel.jsx
        └── data/
            └── villages.js
```

---

## Modifying or Rebuilding the Frontend

If you make modifications to the React code in `frontend/src/`, rebuild the static distribution with:

```bash
cd frontend
npm run build
```

This compiles optimized bundles directly into `../static`, which FastAPI serves automatically on next reload.
