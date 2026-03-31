import React, { useState, useEffect } from 'react'
import { Globe, Users, Activity } from 'lucide-react'
import { regionService } from '../services/api.js'

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

const REGIONS = [
  { id: 'delhi', name: 'Delhi NCR', country: 'India', population: 32000000 },
  { id: 'mumbai', name: 'Mumbai Metropolitan', country: 'India', population: 21000000 },
  { id: 'new_york', name: 'New York City', country: 'USA', population: 8336817 },
  { id: 'london', name: 'Greater London', country: 'UK', population: 9000000 },
  { id: 'tokyo', name: 'Tokyo Metropolis', country: 'Japan', population: 13960000 },
  { id: 'sao_paulo', name: 'Sao Paulo', country: 'Brazil', population: 22043028 },
]

export default function RegionsPage() {
  const [details, setDetails] = useState({})
  const [loadingId, setLoadingId] = useState(null)

  const loadRegion = async (id) => {
    if (details[id]) return
    setLoadingId(id)
    try {
      const data = await regionService.getById(id)
      setDetails(prev => ({ ...prev, [id]: data }))
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingId(null)
    }
  }

  useEffect(() => {
    loadRegion('delhi')
  }, [])

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Region Database</h1>
        <p className="page-subtitle">All available regions for simulation — click to load detailed data</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {REGIONS.map(region => {
          const detail = details[region.id]
          const stats = detail?.disease_stats
          const weather = detail?.weather
          const isLoading = loadingId === region.id

          return (
            <div
              key={region.id}
              className="chart-card"
              style={{ cursor: 'pointer', transition: 'box-shadow 0.15s' }}
              onClick={() => loadRegion(region.id)}
              onMouseEnter={e => e.currentTarget.style.boxShadow = 'var(--shadow-md)'}
              onMouseLeave={e => e.currentTarget.style.boxShadow = 'var(--shadow-sm)'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)' }}>{region.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
                    <Globe size={11} style={{ display: 'inline', marginRight: 4 }} />
                    {region.country}
                  </div>
                </div>
                {isLoading && <div className="spinner" />}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                <div style={{ background: 'var(--color-surface-2)', borderRadius: 6, padding: '8px 10px' }}>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Population</div>
                  <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{fmt(region.population)}</div>
                </div>
                <div style={{ background: 'var(--color-surface-2)', borderRadius: 6, padding: '8px 10px' }}>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Active Cases</div>
                  <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)', color: stats ? 'var(--color-critical)' : 'var(--color-text-muted)' }}>
                    {stats ? fmt(stats.active_cases) : '—'}
                  </div>
                </div>
              </div>

              {stats && (
                <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--color-text-secondary)' }}>
                  <span>R: <strong style={{ fontFamily: 'var(--font-mono)' }}>{stats.reproduction_number}</strong></span>
                  <span>Vacc: <strong>{stats.vaccination_coverage}%</strong></span>
                  {weather && <span>Temp: <strong>{weather.temperature}°C</strong></span>}
                </div>
              )}

              {!detail && !isLoading && (
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 8, fontStyle: 'italic' }}>
                  Click to load region data
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
