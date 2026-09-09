import React from 'react';
import { RISK_COLORS } from '../data/villages';

export default function WarningAlert({
  highestRiskVillage,
  shelter,
  onFocusRoute,
  safeRouteData,
  selectedCandidateId,
  onSelectCandidate,
  activeRouteVillage = 'mahad',
  onSelectRouteCorridor,
}) {
  const currentRoute =
    safeRouteData?.candidates?.find((c) => c.id === selectedCandidateId) ||
    safeRouteData?.candidates?.[0] ||
    safeRouteData;

  const candidates = safeRouteData?.candidates || [];

  const isChiplun = activeRouteVillage === 'chiplun' || safeRouteData?.start?.name?.toLowerCase().includes('chiplun');
  const originDisplay = isChiplun ? 'Chiplun (Ratnagiri)' : 'Mahad (Raigad)';
  const destinationDisplay = isChiplun ? 'Chiplun Relief Shelter' : (shelter?.name || 'Mahad Relief Shelter');

  const risk = currentRoute?.risk_level || highestRiskVillage?.prediction?.risk || 'HIGH';
  const riskTheme = RISK_COLORS[risk] || RISK_COLORS.HIGH;

  return (
    <div
      style={{
        marginTop: '16px',
        backgroundColor: '#ffffff',
        border: `2px solid ${riskTheme.badge}`,
        borderRadius: '12px',
        padding: '20px',
        boxShadow: `0 8px 24px -4px ${riskTheme.badge}20`,
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Route Corridor Switcher */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
        <span style={{ fontSize: '12px', fontWeight: '700', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Select Evacuation Corridor:
        </span>
        <button
          type="button"
          onClick={() => onSelectRouteCorridor && onSelectRouteCorridor('mahad')}
          style={{
            padding: '6px 12px',
            borderRadius: '6px',
            border: !isChiplun ? '2px solid #16a34a' : '1px solid #cbd5e1',
            backgroundColor: !isChiplun ? '#ecfdf5' : '#f8fafc',
            color: !isChiplun ? '#065f46' : '#475569',
            fontWeight: '700',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease',
          }}
        >
          <span>🟢 Mahad ➔ 🔵 Mahad Shelter</span>
          {!isChiplun && (
            <span style={{ fontSize: '10px', background: '#16a34a', color: '#fff', padding: '1px 5px', borderRadius: '3px' }}>
              ACTIVE
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => onSelectRouteCorridor && onSelectRouteCorridor('chiplun')}
          style={{
            padding: '6px 12px',
            borderRadius: '6px',
            border: isChiplun ? '2px solid #dc2626' : '1px solid #cbd5e1',
            backgroundColor: isChiplun ? '#fef2f2' : '#f8fafc',
            color: isChiplun ? '#991b1b' : '#475569',
            fontWeight: '700',
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease',
          }}
        >
          <span>🟢 Chiplun ➔ 🔵 Chiplun Shelter</span>
          {isChiplun && (
            <span style={{ fontSize: '10px', background: '#dc2626', color: '#fff', padding: '1px 5px', borderRadius: '3px' }}>
              ACTIVE
            </span>
          )}
        </button>
      </div>

      {/* 1. Top Flash Flood Alert Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '14px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', flex: 1, minWidth: '280px' }}>
          <span style={{ fontSize: '28px', lineHeight: 1 }}>🚨</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{
                backgroundColor: riskTheme.badge,
                color: '#ffffff',
                fontSize: '11px',
                fontWeight: '800',
                padding: '3px 8px',
                borderRadius: '4px',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
              }}>
                FLASH FLOOD EVACUATION DIRECTIVE
              </span>
              <span style={{ fontSize: '13px', color: '#64748b' }}>
                Origin: <strong>{originDisplay}</strong> ➔ Destination: <strong>{destinationDisplay}</strong>
              </span>
            </div>

            <div style={{ fontSize: '16px', fontWeight: '800', color: '#0f172a', marginTop: '4px' }}>
              Emergency Route Active: Priority Safety Over Shortest Distance
            </div>
          </div>
        </div>

        {onFocusRoute && (
          <button
            onClick={onFocusRoute}
            style={{
              backgroundColor: '#1e3a8a',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 4px rgba(30, 58, 138, 0.25)',
              transition: 'all 0.15s ease',
            }}
          >
            <span>🗺️</span>
            <span>Focus Evacuation Route</span>
          </button>
        )}
      </div>

      {/* 2. Candidate Routes Selection Tabs */}
      {candidates.length > 0 && (
        <div style={{
          backgroundColor: '#f8fafc',
          padding: '12px',
          borderRadius: '10px',
          border: '1px solid #e2e8f0',
        }}>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#475569', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Available Road Network Candidates:
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
            {candidates.map((cand) => {
              const isSelected = (selectedCandidateId || 'safest') === cand.id;
              const candRisk = cand.risk_level || 'HIGH';
              const candTheme = RISK_COLORS[candRisk] || RISK_COLORS.HIGH;

              return (
                <button
                  key={cand.id}
                  onClick={() => onSelectCandidate && onSelectCandidate(cand.id)}
                  style={{
                    backgroundColor: isSelected ? '#ffffff' : '#f1f5f9',
                    border: isSelected ? `2px solid ${cand.recommended ? '#16a34a' : '#2563eb'}` : '1px solid #cbd5e1',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    boxShadow: isSelected ? '0 4px 10px rgba(0,0,0,0.08)' : 'none',
                    transition: 'all 0.15s ease',
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontWeight: '800', fontSize: '13px', color: '#0f172a' }}>
                      {cand.recommended ? '🛡️ ' : '⚡ '}{cand.name}
                    </span>
                    {cand.recommended && (
                      <span style={{
                        backgroundColor: '#dcfce7',
                        color: '#15803d',
                        fontSize: '10px',
                        fontWeight: '800',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        border: '1px solid #86efac',
                      }}>
                        RECOMMENDED
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px', fontSize: '12px', color: '#475569', alignItems: 'center' }}>
                    <span><strong>{cand.distance_km} km</strong></span>
                    <span>•</span>
                    <span>~<strong>{cand.estimated_time_min} min</strong></span>
                    <span>•</span>
                    <span style={{
                      fontWeight: '800',
                      color: candTheme.text,
                      backgroundColor: candTheme.bg,
                      padding: '1px 5px',
                      borderRadius: '3px',
                      fontSize: '11px',
                    }}>
                      {candRisk} RISK
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. Selected Route Statistics Grid */}
      {currentRoute && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '12px',
          backgroundColor: '#f8fafc',
          padding: '14px',
          borderRadius: '10px',
          border: '1px solid #e2e8f0',
        }}>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>TOTAL ROAD DISTANCE</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#0f172a' }}>
              {currentRoute.distance_km} <span style={{ fontSize: '13px', fontWeight: '500' }}>km</span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>EST. TRAVEL TIME</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#0f172a' }}>
              {currentRoute.estimated_time_min} <span style={{ fontSize: '13px', fontWeight: '500' }}>mins</span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>OVERALL ROUTE RISK</div>
            <div style={{
              display: 'inline-block',
              marginTop: '2px',
              fontSize: '13px',
              fontWeight: '800',
              padding: '3px 8px',
              borderRadius: '6px',
              backgroundColor: riskTheme.bg,
              color: riskTheme.text,
              border: `1px solid ${riskTheme.border}`,
            }}>
              {currentRoute.risk_level} RISK
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>HIGH RISK ROAD SECTIONS</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: currentRoute.high_risk_segments > 0 ? '#ea580c' : '#16a34a' }}>
              {currentRoute.high_risk_segments || 0}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>CRITICAL SECTIONS</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: currentRoute.critical_segments > 0 ? '#dc2626' : '#16a34a' }}>
              {currentRoute.critical_segments || 0}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '600' }}>BRIDGE / WATER CROSSINGS</div>
            <div style={{ fontSize: '20px', fontWeight: '800', color: '#0284c7' }}>
              {currentRoute.bridge_crossings || 0} <span style={{ fontSize: '12px', fontWeight: '500' }}>bridges</span>
            </div>
          </div>
        </div>
      )}

      {/* 4. Safety Warnings List */}
      {currentRoute?.warnings && currentRoute.warnings.length > 0 && (
        <div style={{
          backgroundColor: '#fffbeb',
          border: '1px solid #fde68a',
          borderRadius: '8px',
          padding: '12px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}>
          <div style={{ fontSize: '12px', fontWeight: '800', color: '#b45309', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            ⚠️ Operational Safety Guidance & Route Warnings:
          </div>
          <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {currentRoute.warnings.map((warn, idx) => (
              <li key={idx} style={{
                fontSize: '13px',
                color: warn.startsWith('✓') ? '#15803d' : (warn.startsWith('⛔') || warn.includes('CRITICAL')) ? '#dc2626' : '#92400e',
                fontWeight: (warn.startsWith('✓') || warn.includes('CRITICAL')) ? '700' : '500',
              }}>
                {warn}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
