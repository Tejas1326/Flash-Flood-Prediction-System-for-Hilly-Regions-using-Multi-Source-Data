import React from 'react';

export default function Header({ loading, onRefresh, villageCount, highestRisk }) {
  return (
    <header style={{
      backgroundColor: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      padding: '16px 24px',
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '16px',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Government / Disaster Emblem Icon */}
        <div style={{
          width: '46px',
          height: '46px',
          borderRadius: '10px',
          backgroundColor: '#1e3a8a',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: '800',
          fontSize: '20px',
          boxShadow: '0 4px 6px -1px rgba(30, 58, 138, 0.25)',
        }}>
          🌊
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{
              fontSize: '19px',
              fontWeight: '700',
              color: '#0f172a',
              letterSpacing: '-0.02em',
              margin: 0,
            }}>
              FLOOD GUARD AI
            </h1>

          </div>
          <p style={{
            fontSize: '13px',
            color: '#64748b',
            margin: '2px 0 0 0',
          }}>
            Real-time village-level risk prediction & automated emergency evacuation routing • Maharashtra State
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Live Status indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          backgroundColor: '#f1f5f9',
          padding: '6px 12px',
          borderRadius: '8px',
          fontSize: '12px',
          fontWeight: '500',
          color: '#334155',
        }}>
          <span style={{
            width: '9px',
            height: '9px',
            borderRadius: '50%',
            backgroundColor: loading ? '#f59e0b' : '#10b981',
            display: 'inline-block',
            boxShadow: loading ? '0 0 8px #f59e0b' : '0 0 8px #10b981',
          }} />
          <span>{loading ? 'Evaluating Model...' : 'FastAPI Connected'}</span>
          <span style={{ color: '#cbd5e1' }}>|</span>
          <span>{villageCount} Villages Active</span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#ffffff',
            border: '1px solid #cbd5e1',
            padding: '7px 14px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: '600',
            color: '#1e293b',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease',
            opacity: loading ? 0.6 : 1,
          }}
          title="Re-fetch prediction from FastAPI endpoint"
        >
          <span>🔄</span>
          <span>{loading ? 'Fetching...' : 'Re-check Risk'}</span>
        </button>
      </div>
    </header>
  );
}
