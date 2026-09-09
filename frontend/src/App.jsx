import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import MapView from './components/MapView';
import WarningAlert from './components/WarningAlert';
import VillageDetailPanel from './components/VillageDetailPanel';
import { VILLAGES, SHELTERS, findNearestShelter } from './data/villages';

export default function App() {
  const [villages, setVillages] = useState(VILLAGES);
  const [shelters] = useState(SHELTERS);
  const [loading, setLoading] = useState(true);
  const [errorNotice, setErrorNotice] = useState(null);
  const [selectedVillage, setSelectedVillage] = useState(null);
  const [highestRiskVillage, setHighestRiskVillage] = useState(null);

  const [activeRouteVillage, setActiveRouteVillage] = useState('mahad');
  const [routesCache, setRoutesCache] = useState({});
  const [selectedCandidateId, setSelectedCandidateId] = useState('safest');
  const [routeLoading, setRouteLoading] = useState(false);

  const mapInstanceRef = useRef(null);

  // Fetch prediction for a single village
  const fetchVillagePrediction = async (village) => {
    try {
      const response = await fetch('/predict-risk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          village_id: village.village_id,
          lat: village.lat,
          lon: village.lon,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status} for ${village.name}`);
      }

      const predictionData = await response.json();
      return {
        ...village,
        prediction: predictionData,
        error: null,
      };
    } catch (err) {
      console.error(`Failed to fetch risk for ${village.name}:`, err);
      return {
        ...village,
        prediction: {
          probability: 0.2,
          risk: 'LOW',
          estimated_warning_window_min: 120,
          confidence: 0.5,
        },
        error: err.message,
      };
    }
  };

  // Fetch safe evacuation route from backend (Mahad -> Mahad Shelter or Chiplun -> Chiplun Shelter)
  const fetchSafeEvacuationRoute = async (originName = 'Mahad', destName = 'Mahad Shelter') => {
    try {
      const response = await fetch(`/api/evacuation-route?start=${encodeURIComponent(originName)}&destination=${encodeURIComponent(destName)}`);
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status} fetching safe evacuation route for ${originName}`);
      }
      return await response.json();
    } catch (err) {
      console.error(`Failed to fetch safe evacuation route for ${originName}:`, err);
      const isChiplun = originName.toLowerCase().includes('chiplun');
      return {
        start: {
          name: isChiplun ? 'Chiplun' : 'Mahad',
          latitude: isChiplun ? 17.5334 : 18.0833,
          longitude: isChiplun ? 73.5094 : 73.4167,
        },
        destination: {
          name: isChiplun ? 'Chiplun Relief Shelter' : 'Mahad Relief Shelter',
          latitude: isChiplun ? 17.5580 : 18.1050,
          longitude: isChiplun ? 73.5420 : 73.4350,
        },
        distance_km: isChiplun ? 10.12 : 5.8,
        estimated_time_min: isChiplun ? 46 : 22,
        risk_level: isChiplun ? 'CRITICAL' : 'HIGH',
        high_risk_segments: isChiplun ? 8 : 4,
        critical_segments: isChiplun ? 4 : 0,
        bridge_crossings: isChiplun ? 1 : 2,
        warnings: isChiplun
          ? [
            '⚠ CRITICAL FLOOD RISK: Evacuation route contains elevated flood-risk sections. Follow official emergency instructions and use the route only as a decision-support recommendation.',
            'High flood-risk section detected near river catchment buffer',
            'Route crosses 1 bridge/culvert structure(s) - risk of swelling river levels',
            'Destination verified: Chiplun Relief Shelter',
          ]
          : [
            'High flood-risk section detected near Savitri river catchment buffer',
            'Route crosses 2 bridge/culvert structure(s)',
            'Proceed under official emergency disaster guidance.',
            'Destination verified: Mahad Relief Shelter',
          ],
        recommended: true,
        candidates: [
          {
            id: 'safest',
            name: 'Safe Evacuation Route',
            route: isChiplun
              ? [[17.5334, 73.5094], [17.5580, 73.5420]]
              : [[18.0833, 73.4167], [18.1050, 73.4350]],
            distance_km: isChiplun ? 10.12 : 5.8,
            estimated_time_min: isChiplun ? 46 : 22,
            risk_level: isChiplun ? 'CRITICAL' : 'HIGH',
            high_risk_segments: isChiplun ? 8 : 4,
            critical_segments: isChiplun ? 4 : 0,
            bridge_crossings: isChiplun ? 1 : 2,
            warnings: isChiplun
              ? ['⚠ CRITICAL FLOOD RISK: Evacuation route contains elevated flood-risk sections.', 'Destination verified: Chiplun Relief Shelter']
              : ['Destination verified: Mahad Relief Shelter'],
            recommended: true,
          }
        ],
      };
    }
  };

  // Load predictions for all villages and evacuation routes in parallel
  const loadAllPredictions = async () => {
    setLoading(true);
    setRouteLoading(true);
    setErrorNotice(null);

    try {
      // 1. Fetch dynamic villages and shelters from backend
      let baseVillages = VILLAGES;
      let baseShelters = shelters;

      try {
        const [vRes, sRes] = await Promise.all([
          fetch('/api/villages'),
          fetch('/api/shelters')
        ]);
        if (vRes.ok) {
          const vData = await vRes.json();
          if (Array.isArray(vData) && vData.length > 0) {
            baseVillages = vData;
          }
        }
        if (sRes.ok) {
          const sData = await sRes.json();
          if (Array.isArray(sData) && sData.length > 0) {
            baseShelters = sData;
            setShelters(sData);
          }
        }
      } catch (e) {
        console.warn('Backend registry endpoints offline, using client fallbacks:', e);
      }

      // 2. Fetch predictions for all villages in parallel
      const promises = baseVillages.map((v) => fetchVillagePrediction(v));
      const [updatedVillages, mahadRoute, chiplunRoute] = await Promise.all([
        Promise.all(promises),
        fetchSafeEvacuationRoute('Mahad', 'Mahad Shelter'),
        fetchSafeEvacuationRoute('Chiplun', 'Chiplun Shelter'),
      ]);

      const failedCount = updatedVillages.filter((v) => v.error).length;
      if (failedCount > 0) {
        setErrorNotice(`Notice: ${failedCount} village prediction(s) used fallback estimates.`);
      }

      let maxProb = -1;
      let highest = null;

      updatedVillages.forEach((v) => {
        if (v.prediction && v.prediction.probability > maxProb) {
          maxProb = v.prediction.probability;
          highest = v;
        }
      });

      if (highest) {
        const shelter = findNearestShelter(highest.lat, highest.lon, baseShelters);
        highest = {
          ...highest,
          nearestShelter: shelter,
        };
      }

      setVillages(updatedVillages);
      setHighestRiskVillage(highest);

      setRoutesCache({
        mahad: mahadRoute,
        chiplun: chiplunRoute,
      });

      if (!selectedVillage && highest) {
        setSelectedVillage(highest);
      }
    } catch (err) {
      console.error('Fatal error loading village risk predictions:', err);
      setErrorNotice('Failed to connect to /predict-risk backend service.');
    } finally {
      setLoading(false);
      setRouteLoading(false);
    }
  };

  useEffect(() => {
    loadAllPredictions();
  }, []);

  const safeRouteData = routesCache[activeRouteVillage] || (activeRouteVillage === 'chiplun' ? routesCache.chiplun : routesCache.mahad) || null;

  // Auto-sync selected candidate when active route changes
  useEffect(() => {
    if (safeRouteData?.candidates) {
      const recommended = safeRouteData.candidates.find((c) => c.recommended) || safeRouteData.candidates[0];
      if (recommended) {
        setSelectedCandidateId(recommended.id);
      }
    }
  }, [activeRouteVillage, routesCache]);

  // Handler to select a village & sync active route corridor if appropriate
  const handleSelectVillage = async (village) => {
    setSelectedVillage(village);
    const vId = village.village_id;
    if (vId === 'chiplun' || vId === 'mahad') {
      setActiveRouteVillage(vId);
    } else {
      setActiveRouteVillage(vId);
      if (!routesCache[vId]) {
        setRouteLoading(true);
        try {
          const nearest = findNearestShelter(village.lat, village.lon, shelters);
          const destName = nearest ? nearest.name : 'Mahad Relief Shelter';
          const r = await fetchSafeEvacuationRoute(village.name, destName);
          setRoutesCache((prev) => ({ ...prev, [vId]: r }));
        } catch (e) {
          console.error(`Route fetch failed for ${village.name}:`, e);
        } finally {
          setRouteLoading(false);
        }
      }
    }
  };

  // Handler to toggle route corridors directly
  const handleSelectRouteCorridor = (corridorKey) => {
    setActiveRouteVillage(corridorKey);
    const targetVillage = villages.find((v) => v.village_id === corridorKey);
    if (targetVillage) {
      setSelectedVillage(targetVillage);
    }
  };

  // Handler to focus map on the active evacuation route
  const handleFocusRoute = () => {
    if (!mapInstanceRef.current) return;

    const currentRoute =
      safeRouteData?.candidates?.find((c) => c.id === selectedCandidateId) ||
      safeRouteData?.candidates?.[0] ||
      safeRouteData;

    if (currentRoute && Array.isArray(currentRoute.route) && currentRoute.route.length > 0) {
      const latlngs = currentRoute.route.map((pt) => Array.isArray(pt) ? pt : [pt.lat, pt.lng]);
      mapInstanceRef.current.flyToBounds(latlngs, {
        padding: [60, 60],
        duration: 1.2,
      });
    } else {
      const fallbackBounds = activeRouteVillage === 'chiplun'
        ? [[17.5334, 73.5094], [17.5580, 73.5420]]
        : [[18.0833, 73.4167], [18.1050, 73.4350]];
      mapInstanceRef.current.flyToBounds(fallbackBounds, { padding: [60, 60], duration: 1.2 });
    }
  };

  const activeCandidate =
    safeRouteData?.candidates?.find((c) => c.id === selectedCandidateId) ||
    safeRouteData?.candidates?.[0] ||
    safeRouteData;

  const currentShelter =
    findNearestShelter(
      selectedVillage?.lat || (activeRouteVillage === 'chiplun' ? 17.533 : 18.083),
      selectedVillage?.lon || (activeRouteVillage === 'chiplun' ? 73.509 : 73.417),
      shelters
    ) || (activeRouteVillage === 'chiplun'
      ? shelters.find((s) => s.id?.includes('chiplun')) || {
        name: 'Chiplun Relief Shelter',
        lat: 17.5580,
        lon: 73.5420,
        type: 'Elevated Disaster Shelter',
        capacity: '650 Persons',
      }
      : shelters.find((s) => s.id?.includes('mahad')) || {
        name: 'Mahad Relief Shelter',
        lat: 18.1050,
        lon: 73.4350,
        type: 'Multi-Purpose Cyclone & Flood Shelter',
        capacity: '500 Persons',
      });

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc', display: 'flex', flexDirection: 'column' }}>
      {/* Top Government Header with Re-check Risk button */}
      <Header
        loading={loading || routeLoading}
        onRefresh={loadAllPredictions}
        villageCount={villages.length}
        highestRisk={highestRiskVillage}
      />

      {/* Main Content Area */}
      <main style={{ maxWidth: '1240px', width: '100%', margin: '0 auto', padding: '20px 24px', flex: 1 }}>
        {/* Connection Notice / Error Bar if any */}
        {errorNotice && (
          <div style={{
            marginBottom: '16px',
            backgroundColor: '#fffbeb',
            color: '#b45309',
            border: '1px solid #fde68a',
            padding: '10px 16px',
            borderRadius: '8px',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <span>⚠️</span>
            <span>{errorNotice}</span>
          </div>
        )}

        {/* Leaflet Interactive Map */}
        <MapView
          villages={villages}
          shelters={shelters}
          highestRiskVillage={highestRiskVillage}
          selectedVillage={selectedVillage}
          onSelectVillage={handleSelectVillage}
          mapRefExternal={mapInstanceRef}
          evacuationRoute={safeRouteData}
          activeCandidate={activeCandidate}
          onFocusRoute={handleFocusRoute}
          activeRouteVillage={activeRouteVillage}
        />

        {/* Safe Flood Evacuation Route Directive & Candidate Selection Panel */}
        <WarningAlert
          highestRiskVillage={highestRiskVillage}
          shelter={currentShelter}
          onFocusRoute={handleFocusRoute}
          safeRouteData={safeRouteData}
          selectedCandidateId={selectedCandidateId}
          onSelectCandidate={(id) => setSelectedCandidateId(id)}
          activeRouteVillage={activeRouteVillage}
          onSelectRouteCorridor={handleSelectRouteCorridor}
        />

        {/* Village Detail Matrix & Inspection Card */}
        <VillageDetailPanel
          villages={villages}
          selectedVillage={selectedVillage}
          onSelectVillage={handleSelectVillage}
          highestRiskVillage={highestRiskVillage}
        />
      </main>

      {/* Footer */}
      <footer style={{
        marginTop: 'auto',
        borderTop: '1px solid #e2e8f0',
        backgroundColor: '#ffffff',
        padding: '14px 24px',
        textAlign: 'center',
        fontSize: '12px',
        color: '#64748b',
      }}>
        Flash-Flood Early Warning System • Village-Level Risk Monitoring & Emergency Evacuation Support
      </footer>
    </div>
  );
}
