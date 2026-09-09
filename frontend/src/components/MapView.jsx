import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RISK_COLORS } from '../data/villages';

export default function MapView({
  villages,
  shelters,
  highestRiskVillage,
  selectedVillage,
  onSelectVillage,
  mapRefExternal,
  evacuationRoute,
  activeCandidate,
  onFocusRoute,
  activeRouteVillage = 'taliye',
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const zoneLayerGroupRef = useRef(null);
  const villageLayerGroupRef = useRef(null);
  const shelterLayerGroupRef = useRef(null);
  const routePolylineRef = useRef(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Centered on Konkan Region around Lat: ~18.10, Lon: ~73.50
    const map = L.map(mapContainerRef.current, {
      center: [18.09, 73.50],
      zoom: 11,
      zoomControl: true,

      // Hide Leaflet attribution box
      attributionControl: false,
    });

    // OpenStreetMap standard tile layer
    // Leaflet is still being used normally.
    L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxZoom: 18,
      }
    ).addTo(map);

    // Layer groups for danger zones, markers, and shelter overlays
    zoneLayerGroupRef.current = L.layerGroup().addTo(map);
    villageLayerGroupRef.current = L.layerGroup().addTo(map);
    shelterLayerGroupRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    if (mapRefExternal) {
      mapRefExternal.current = map;
    }

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Shelter Markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const shelterGroup = shelterLayerGroupRef.current;

    if (!map || !shelterGroup) return;

    shelterGroup.clearLayers();

    shelters.forEach((shelter) => {
      const isTargetShelter =
        activeRouteVillage === 'chiplun'
          ? (
              shelter.id === 'shelter-chiplun' ||
              shelter.name
                .toLowerCase()
                .includes('chiplun')
            )
          : (
              shelter.id === 'shelter-mahad' ||
              shelter.name
                .toLowerCase()
                .includes('mahad')
            );

      const shelterLabel =
        activeRouteVillage === 'chiplun'
          ? '🔵 DESTINATION: Chiplun Shelter'
          : '🔵 DESTINATION: Mahad Shelter';

      const icon = L.divIcon({
        className: 'custom-village-pin',

        iconSize: isTargetShelter
          ? [44, 58]
          : [36, 52],

        iconAnchor: isTargetShelter
          ? [22, 54]
          : [18, 50],

        popupAnchor: [0, -48],

        html: `
          <div class="pin-container">
            <div
              class="${
                isTargetShelter
                  ? 'shelter-bubble-highlight'
                  : 'shelter-bubble'
              }"
              title="${
                isTargetShelter
                  ? `Designated Destination Shelter: ${shelter.name}`
                  : 'Emergency Shelter'
              }"
            >
              <span
                style="
                  font-size: ${
                    isTargetShelter ? '20px' : '16px'
                  };
                "
              >
                🏛️
              </span>
            </div>

            <div
              class="${
                isTargetShelter
                  ? 'shelter-label-highlight'
                  : 'shelter-label'
              }"
            >
              ${
                isTargetShelter
                  ? shelterLabel
                  : `Shelter: ${shelter.name.split(' ')[0]}`
              }
            </div>
          </div>
        `,
      });

      const marker = L.marker(
        [shelter.lat, shelter.lon],
        { icon }
      ).addTo(shelterGroup);

      const popupContent = `
        <div
          style="
            font-family: 'Inter', sans-serif;
            min-width: 220px;
          "
        >
          <div
            style="
              font-size: 11px;
              font-weight: 700;
              color: #2563eb;
              text-transform: uppercase;
              margin-bottom: 2px;
            "
          >
            ${
              isTargetShelter
                ? 'Official Evacuation Destination'
                : 'Emergency Flood Relief Shelter'
            }
          </div>

          <div
            style="
              font-size: 14px;
              font-weight: 700;
              color: #0f172a;
              margin-bottom: 6px;
            "
          >
            ${shelter.name}
          </div>

          <div
            style="
              font-size: 12px;
              color: #475569;
              line-height: 1.5;
            "
          >
            <div>
              <strong>Type:</strong>
              ${shelter.type || 'N/A'}
            </div>

            <div>
              <strong>Capacity:</strong>
              ${shelter.capacity || 'N/A'}
            </div>

            <div>
              <strong>Coordinates:</strong>
              ${
                shelter.lat
                  ? shelter.lat.toFixed(4)
                  : 'N/A'
              }° N,
              ${
                shelter.lon
                  ? shelter.lon.toFixed(4)
                  : 'N/A'
              }° E
            </div>
          </div>

          <div
            style="
              margin-top: 8px;
              font-size: 11px;
              background: #eff6ff;
              color: #1e40af;
              padding: 4px 8px;
              border-radius: 4px;
              border: 1px solid #bfdbfe;
              font-weight: 600;
            "
          >
            ✓ Safe elevated high-ground shelter
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
    });
  }, [shelters, activeRouteVillage]);

  // Update Danger Zone circles and Village Markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const zoneGroup = zoneLayerGroupRef.current;
    const villageGroup = villageLayerGroupRef.current;

    if (
      !map ||
      !villageGroup ||
      !zoneGroup
    ) {
      return;
    }

    villageGroup.clearLayers();
    zoneGroup.clearLayers();

    const riskPriority = {
      LOW: 1,
      MODERATE: 2,
      HIGH: 3,
      CRITICAL: 4,
    };

    const sortedVillages = [...villages].sort(
      (a, b) => {
        const riskA = a.prediction
          ? a.prediction.risk
          : 'LOW';

        const riskB = b.prediction
          ? b.prediction.risk
          : 'LOW';

        return (
          (riskPriority[riskA] || 1) -
          (riskPriority[riskB] || 1)
        );
      }
    );

    // 1. Render Danger Zone Buffer Circles
    sortedVillages.forEach((village) => {
      const pred = village.prediction;

      const risk = pred
        ? pred.risk
        : 'LOW';

      const riskConfig =
        RISK_COLORS[risk] ||
        RISK_COLORS.LOW;

      L.circle(
        [village.lat, village.lon],
        {
          radius:
            riskConfig.radius || 3000,

          color: riskConfig.fill,

          weight: 2,

          opacity: 0.85,

          fillColor: riskConfig.fill,

          fillOpacity: 0.20,

          interactive: false,
        }
      ).addTo(zoneGroup);
    });

    // 2. Render Village Point Markers
    villages.forEach((village) => {
      const pred = village.prediction;

      const risk = pred
        ? pred.risk
        : 'LOW';

      const riskConfig =
        RISK_COLORS[risk] ||
        RISK_COLORS.LOW;

      const isHighest =
        highestRiskVillage &&
        highestRiskVillage.village_id ===
          village.village_id;

      const isStartPoint =
        (
          activeRouteVillage === 'chiplun' &&
          (
            village.village_id === 'chiplun' ||
            village.name
              .toLowerCase() === 'chiplun'
          )
        ) ||
        (
          activeRouteVillage === 'taliye' &&
          (
            village.village_id === 'taliye' ||
            village.name
              .toLowerCase() === 'taliye'
          )
        );

      const pulseRing =
        isStartPoint
          ? `
            <div
              class="pin-pulse"
              style="
                background: #16a34a;
              "
            ></div>
          `
          : risk === 'CRITICAL' ||
            isHighest
            ? `
              <div
                class="pin-pulse"
                style="
                  background: ${riskConfig.badge};
                "
              ></div>
            `
            : '';

      const icon = L.divIcon({
        className:
          'custom-village-pin',

        iconSize:
          isStartPoint
            ? [42, 58]
            : [36, 52],

        iconAnchor:
          isStartPoint
            ? [21, 54]
            : [18, 50],

        popupAnchor: [0, -48],

        html: `
          <div class="pin-container">

            <div
              class="${
                isStartPoint
                  ? 'start-bubble'
                  : 'pin-bubble'
              }"
              style="${
                isStartPoint
                  ? ''
                  : `
                    background: ${riskConfig.fill};
                    border-color: #ffffff;
                  `
              }"
            >

              ${pulseRing}

              <span
                style="
                  font-size: 14px;
                "
              >
                ${
                  isStartPoint
                    ? '🟢'
                    : isHighest
                      ? '⚠️'
                      : '📍'
                }
              </span>

            </div>

            <div
              class="${
                isStartPoint
                  ? 'start-label'
                  : 'pin-label'
              }"
              style="${
                isStartPoint
                  ? ''
                  : `
                    background: ${
                      isHighest
                        ? '#7f1d1d'
                        : 'rgba(15, 23, 42, 0.9)'
                    };
                  `
              }"
            >
              ${
                isStartPoint
                  ? `🟢 START: ${village.name}`
                  : `${village.name} ${
                      pred
                        ? `(${risk})`
                        : ''
                    }`
              }
            </div>

          </div>
        `,
      });

      const marker = L.marker(
        [village.lat, village.lon],
        { icon }
      ).addTo(villageGroup);

      const probPercent =
        pred &&
        pred.probability != null
          ? `${Math.round(
              pred.probability * 100
            )}%`
          : 'N/A';

      const confidencePercent =
        pred &&
        pred.confidence != null
          ? `${Math.round(
              pred.confidence * 100
            )}%`
          : 'N/A';

      const windowMin =
        pred &&
        pred.estimated_warning_window_min != null
          ? `${pred.estimated_warning_window_min} mins`
          : 'N/A';

      const popupHtml = `
        <div
          style="
            font-family: 'Inter', sans-serif;
            min-width: 220px;
          "
        >

          <div
            style="
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              margin-bottom: 4px;
            "
          >

            <div
              style="
                font-size: 15px;
                font-weight: 700;
                color: #0f172a;
              "
            >
              ${
                isStartPoint
                  ? `🟢 ${village.name} (Evacuation Origin)`
                  : village.name
              }
            </div>

            <span
              style="
                background: ${riskConfig.bg};
                color: ${riskConfig.text};
                border: 1px solid ${riskConfig.border};
                font-size: 11px;
                font-weight: 800;
                padding: 2px 7px;
                border-radius: 4px;
              "
            >
              ${risk}
            </span>

          </div>

          <div
            style="
              font-size: 11px;
              color: #64748b;
              margin-bottom: 8px;
            "
          >
            District:
            ${village.district || 'N/A'}
            •
            Basin:
            ${village.river_basin || 'N/A'}
          </div>

          <div
            style="
              border-top: 1px solid #e2e8f0;
              padding-top: 6px;
              display: flex;
              flex-direction: column;
              gap: 4px;
              font-size: 12px;
              color: #334155;
            "
          >

            <div
              style="
                display: flex;
                justify-content: space-between;
              "
            >
              <span
                style="
                  color: #64748b;
                "
              >
                Flash-Flood Risk:
              </span>

              <strong
                style="
                  color: ${riskConfig.text};
                "
              >
                ${probPercent}
              </strong>
            </div>

            <div
              style="
                display: flex;
                justify-content: space-between;
              "
            >
              <span
                style="
                  color: #64748b;
                "
              >
                Est. Warning Window:
              </span>

              <strong>
                ${windowMin}
              </strong>
            </div>

            <div
              style="
                display: flex;
                justify-content: space-between;
              "
            >
              <span
                style="
                  color: #64748b;
                "
              >
                Model Confidence:
              </span>

              <strong>
                ${confidencePercent}
              </strong>
            </div>

            <div
              style="
                display: flex;
                justify-content: space-between;
              "
            >
              <span
                style="
                  color: #64748b;
                "
              >
                Coordinates:
              </span>

              <span>
                ${
                  village.lat
                    ? village.lat.toFixed(4)
                    : 'N/A'
                }°,
                ${
                  village.lon
                    ? village.lon.toFixed(4)
                    : 'N/A'
                }°
              </span>
            </div>

          </div>

          ${
            isStartPoint
              ? `
                <div
                  style="
                    margin-top: 8px;
                    background: #ecfdf5;
                    border: 1px solid #a7f3d0;
                    color: #065f46;
                    padding: 4px 6px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: center;
                  "
                >
                  🟢 Designated Start Point
                  for Flood Evacuation Routing
                </div>
              `
              : isHighest
                ? `
                  <div
                    style="
                      margin-top: 8px;
                      background: #fee2e2;
                      border: 1px solid #fca5a5;
                      color: #991b1b;
                      padding: 4px 6px;
                      border-radius: 4px;
                      font-size: 11px;
                      font-weight: 600;
                      text-align: center;
                    "
                  >
                    ⚠️ Highest Flood Risk Detected
                    — Evacuate to Shelter
                  </div>
                `
                : ''
          }

        </div>
      `;

      marker.bindPopup(popupHtml);

      marker.on('click', () => {
        if (onSelectVillage) {
          onSelectVillage(village);
        }
      });
    });
  }, [
    villages,
    highestRiskVillage,
    activeRouteVillage,
    onSelectVillage,
  ]);

  // Update Evacuation Route Polyline
  useEffect(() => {
    const map = mapInstanceRef.current;

    if (!map) return;

    if (routePolylineRef.current) {
      map.removeLayer(
        routePolylineRef.current
      );

      routePolylineRef.current = null;
    }

    const routeData =
      activeCandidate ||
      evacuationRoute;

    if (!routeData) return;

    let latlngs = [];

    if (
      Array.isArray(routeData.route) &&
      routeData.route.length > 0
    ) {
      // Objects {lat, lng} or pairs [lat, lng]
      latlngs =
        routeData.route.map(
          (pt) =>
            Array.isArray(pt)
              ? pt
              : [pt.lat, pt.lng]
        );
    } else if (
      Array.isArray(routeData.coordinates) &&
      routeData.coordinates.length > 0
    ) {
      latlngs =
        routeData.coordinates;
    }

    if (latlngs.length > 0) {
      const riskLvl =
        routeData.risk_level ||
        'HIGH';

      const routeColor =
        riskLvl === 'CRITICAL'
          ? '#dc2626'
          : riskLvl === 'HIGH'
            ? '#ea580c'
            : riskLvl === 'MODERATE'
              ? '#ca8a04'
              : '#16a34a';

      const polyline =
        L.polyline(
          latlngs,
          {
            color: routeColor,
            weight:
              routeData.recommended
                ? 6
                : 4,
            opacity: 0.95,
            dashArray: '10, 8',
            lineCap: 'round',
            lineJoin: 'round',
            className:
              'evacuation-route-line',
          }
        ).addTo(map);

      const distKm =
        routeData.distance_km || 0;

      const timeMin =
        routeData.estimated_time_min ||
        0;

      const title =
        routeData.name ||
        (
          routeData.recommended
            ? 'Recommended Safe Evacuation Route'
            : 'Evacuation Route'
        );

      // Changed from "OpenStreetMap Network"
      // to avoid displaying OpenStreetMap name.
      const roadList =
        routeData.road_names &&
        routeData.road_names.length > 0
          ? routeData.road_names
              .slice(0, 5)
              .join(', ')
          : 'Road Network';

      const startName =
        routeData.start?.name ||
        (
          activeRouteVillage === 'chiplun'
            ? 'Chiplun'
            : 'Taliye'
        );

      const destName =
        routeData.destination?.name ||
        (
          activeRouteVillage === 'chiplun'
            ? 'Chiplun Relief Shelter'
            : 'Mahad Relief Shelter'
        );

      polyline.bindTooltip(
        `<div
          style="
            font-family: Inter, sans-serif;
            font-size: 12px;
          "
        >
          <strong>
            ${title}
          </strong>

          ${
            distKm
              ? `(${distKm} km • ~${timeMin} min)`
              : ''
          }

          <br/>

          🟢 ${startName}
          ➔
          🔵 ${destName}

          <br/>

          <span
            style="
              color: ${routeColor};
              font-weight: 700;
            "
          >
            Route Risk: ${riskLvl}
          </span>

          • Bridges:
          ${routeData.bridge_crossings || 0}

          <br/>

          <span
            style="
              font-size: 11px;
              color: #64748b;
            "
          >
            Key Roads:
            ${roadList}
          </span>
        </div>`,
        {
          sticky: true,
          className: 'route-tooltip',
        }
      );

      routePolylineRef.current =
        polyline;
    }
  }, [
    activeCandidate,
    evacuationRoute,
    activeRouteVillage,
  ]);

  const currentRoute =
    activeCandidate ||
    evacuationRoute;

  const startName =
    currentRoute?.start?.name ||
    (
      activeRouteVillage === 'chiplun'
        ? 'Chiplun'
        : 'Taliye'
    );

  const destName =
    currentRoute?.destination?.name ||
    (
      activeRouteVillage === 'chiplun'
        ? 'Chiplun Shelter'
        : 'Mahad Shelter'
    );

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '560px',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow:
          '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        border:
          '1px solid #e2e8f0',
      }}
    >

      {/* Map Container */}
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
        }}
      />

      {/* Floating Evacuation Status Bar */}
      {currentRoute && (
        <div
          style={{
            position: 'absolute',
            top: '12px',
            left: '12px',
            zIndex: 1000,
            backgroundColor:
              'rgba(255, 255, 255, 0.96)',
            backdropFilter:
              'blur(8px)',
            borderRadius: '10px',
            padding: '10px 14px',
            boxShadow:
              '0 6px 16px rgba(0, 0, 0, 0.12)',
            border:
              '1px solid #cbd5e1',
            fontSize: '12px',
            fontFamily:
              "'Inter', sans-serif",
            maxWidth: '360px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent:
                'space-between',
              gap: '8px',
            }}
          >

            <span
              style={{
                fontWeight: '800',
                color: '#0f172a',
                fontSize: '13px',
              }}
            >
              🟢 {startName}
              ➔
              🔵 {destName}
            </span>

            <span
              style={{
                fontSize: '10px',
                fontWeight: '800',
                padding: '2px 6px',
                borderRadius: '4px',
                backgroundColor:
                  currentRoute.recommended
                    ? '#dcfce7'
                    : '#f1f5f9',
                color:
                  currentRoute.recommended
                    ? '#15803d'
                    : '#475569',
                border:
                  currentRoute.recommended
                    ? '1px solid #86efac'
                    : '1px solid #cbd5e1',
              }}
            >
              {
                currentRoute.recommended
                  ? 'SAFEST ROUTE'
                  : currentRoute.id
                    ?.toUpperCase() ||
                    'ROUTE'
              }
            </span>

          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              color: '#334155',
              fontSize: '12px',
            }}
          >

            <span>
              <strong>
                Distance:
              </strong>{' '}
              {currentRoute.distance_km}
              {' '}
              km
            </span>

            <span>•</span>

            <span>
              <strong>
                Est. Time:
              </strong>{' '}
              {
                currentRoute.estimated_time_min
              }
              {' '}
              min
            </span>

            <span>•</span>

            <span
              style={{
                fontWeight: '700',
                color:
                  currentRoute.risk_level ===
                  'CRITICAL'
                    ? '#dc2626'
                    : currentRoute.risk_level ===
                      'HIGH'
                      ? '#ea580c'
                      : '#16a34a',
              }}
            >
              {currentRoute.risk_level}
            </span>

          </div>

          {onFocusRoute && (
            <button
              onClick={onFocusRoute}
              style={{
                marginTop: '2px',
                backgroundColor:
                  '#1e3a8a',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: '600',
                cursor: 'pointer',
                alignSelf:
                  'flex-start',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              🔍 Focus Route on Map
            </button>
          )}

        </div>
      )}

      {/* Map Legend Overlay */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          zIndex: 1000,
          backgroundColor:
            'rgba(255, 255, 255, 0.95)',
          backdropFilter:
            'blur(6px)',
          borderRadius: '8px',
          padding: '12px 14px',
          boxShadow:
            '0 4px 12px rgba(0,0,0,0.12)',
          border:
            '1px solid #e2e8f0',
          fontSize: '11px',
          fontFamily:
            "'Inter', sans-serif",
          maxWidth: '220px',
        }}
      >

        <div
          style={{
            fontWeight: '700',
            color: '#0f172a',
            marginBottom: '8px',
            fontSize: '12px',
            borderBottom:
              '1px solid #f1f5f9',
            paddingBottom: '4px',
          }}
        >
          Flood Evacuation Legend
        </div>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '5px',
          }}
        >

          {/* Start */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor:
                  '#16a34a',
                display: 'inline-block',
              }}
            />

            <span
              style={{
                color: '#0f172a',
                fontWeight: '700',
              }}
            >
              🟢 Start:{' '}
              {
                activeRouteVillage ===
                'chiplun'
                  ? 'Chiplun'
                  : 'Taliye'
              }{' '}
              Village
            </span>
          </div>

          {/* Destination */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '3px',
                backgroundColor:
                  '#1d4ed8',
                color: '#fff',
                fontSize: '9px',
                display: 'flex',
                alignItems: 'center',
                justifyContent:
                  'center',
              }}
            >
              🏛️
            </span>

            <span
              style={{
                color: '#1e3a8a',
                fontWeight: '700',
              }}
            >
              🔵 Dest:{' '}
              {
                activeRouteVillage ===
                'chiplun'
                  ? 'Chiplun'
                  : 'Mahad'
              }{' '}
              Shelter
            </span>
          </div>

          {/* Route */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '16px',
                height: '0px',
                borderTop:
                  '3px dashed #ea580c',
                display: 'inline-block',
              }}
            />

            <span
              style={{
                color: '#c2410c',
                fontWeight: '600',
              }}
            >
              Evacuation Road Route
            </span>
          </div>

          {/* Flood Buffer */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '13px',
                height: '13px',
                borderRadius: '50%',
                border:
                  '2px solid #ef4444',
                backgroundColor:
                  'rgba(239, 68, 68, 0.2)',
                display: 'inline-block',
              }}
            />

            <span
              style={{
                color: '#0f172a',
                fontWeight: '600',
              }}
            >
              Flood Risk Buffer
              (3-7km)
            </span>
          </div>

          <div
            style={{
              height: '1px',
              backgroundColor:
                '#e2e8f0',
              margin: '4px 0',
            }}
          />

          {/* Critical */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor:
                  RISK_COLORS.CRITICAL
                    .fill,
                display: 'inline-block',
              }}
            />

            <span
              style={{
                color: '#0f172a',
              }}
            >
              CRITICAL
              (&ge; 80%)
            </span>
          </div>

          {/* High */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor:
                  RISK_COLORS.HIGH
                    .fill,
                display: 'inline-block',
              }}
            />

            <span
              style={{
                color: '#0f172a',
              }}
            >
              HIGH
              (60% - 79%)
            </span>
          </div>

          {/* Low */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor:
                  RISK_COLORS.LOW
                    .fill,
                display: 'inline-block',
              }}
            />

            <span
              style={{
                color: '#0f172a',
              }}
            >
              LOW
              (&lt; 35%)
            </span>
          </div>

        </div>
      </div>

    </div>
  );
}