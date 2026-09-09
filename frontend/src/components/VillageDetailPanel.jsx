import React from 'react';
import { RISK_COLORS } from '../data/villages';

export default function VillageDetailPanel({
  villages,
  selectedVillage,
  onSelectVillage,
  highestRiskVillage,
}) {
  const activeVillage = selectedVillage || highestRiskVillage || villages[0];
  const pred = activeVillage?.prediction;
  const risk = pred?.risk || 'LOW';
  const riskTheme = RISK_COLORS[risk] || RISK_COLORS.LOW;

  return (
    <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Village Quick Status Grid / Table */}
      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '10px',
        padding: '16px 20px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
          borderBottom: '1px solid #f1f5f9',
          paddingBottom: '8px',
        }}>
          <h2 style={{ fontSize: '15px', fontWeight: '700', color: '#0f172a', margin: 0 }}>
            Village Risk Matrix — Konkan Catchment Zone
          </h2>
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            Click any village to inspect details
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '10px',
        }}>
          {villages.map((v) => {
            const vPred = v.prediction;
            const vRisk = vPred?.risk || 'LOW';
            const theme = RISK_COLORS[vRisk] || RISK_COLORS.LOW;
            const isSelected = activeVillage?.village_id === v.village_id;
            const isHighest = highestRiskVillage?.village_id === v.village_id;

            return (
              <button
                key={v.village_id}
                onClick={() => onSelectVillage(v)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: isSelected ? `2px solid ${theme.badge}` : '1px solid #e2e8f0',
                  backgroundColor: isSelected ? theme.bg : '#ffffff',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease',
                  position: 'relative',
                }}
              >
                {isHighest && (
                  <span style={{
                    position: 'absolute',
                    top: '-6px',
                    right: '-4px',
                    backgroundColor: '#dc2626',
                    color: '#ffffff',
                    fontSize: '9px',
                    fontWeight: '800',
                    padding: '1px 5px',
                    borderRadius: '4px',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                  }}>
                    ALERT
                  </span>
                )}
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#0f172a' }}>
                  {v.name}
                </div>
                <div style={{
                  fontSize: '11px',
                  fontWeight: '800',
                  color: theme.text,
                  marginTop: '4px',
                }}>
                  {vRisk} {vPred ? `(${Math.round(vPred.probability * 100)}%)` : ''}
                </div>
                <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
                  Onset: {vPred ? `${vPred.estimated_warning_window_min}m` : '--'}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Village Detailed Card */}
      {activeVillage && (
        <div style={{
          backgroundColor: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '10px',
          padding: '16px 20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>📌</span>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', margin: 0 }}>
                Selected Village: {activeVillage.name}
              </h3>
              <span style={{
                fontSize: '12px',
                fontWeight: '700',
                backgroundColor: riskTheme.bg,
                color: riskTheme.text,
                border: `1px solid ${riskTheme.border}`,
                padding: '2px 8px',
                borderRadius: '4px',
              }}>
                {risk} RISK
              </span>
            </div>
            <p style={{ fontSize: '12px', color: '#64748b', margin: '4px 0 0 26px' }}>
              District: {activeVillage.district} • Basin: {activeVillage.river_basin} • Coordinates: {activeVillage.lat}° N, {activeVillage.lon}° E
            </p>
          </div>

          {pred ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
              <div style={{ textAlign: 'center', padding: '0 8px' }}>
                <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '500' }}>Flash-Flood Risk</div>
                <div style={{ fontSize: '18px', fontWeight: '800', color: riskTheme.text }}>
                  {Math.round(pred.probability * 100)}%
                </div>
              </div>
              <div style={{ textAlign: 'center', padding: '0 8px', borderLeft: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '500' }}>Warning Window</div>
                <div style={{ fontSize: '18px', fontWeight: '800', color: '#0f172a' }}>
                  {pred.estimated_warning_window_min} min
                </div>
              </div>
              <div style={{ textAlign: 'center', padding: '0 8px', borderLeft: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '500' }}>Model Confidence</div>
                <div style={{ fontSize: '18px', fontWeight: '800', color: '#0f172a' }}>
                  {Math.round(pred.confidence * 100)}%
                </div>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: '13px', color: '#64748b' }}>
              Fetching prediction from backend...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
