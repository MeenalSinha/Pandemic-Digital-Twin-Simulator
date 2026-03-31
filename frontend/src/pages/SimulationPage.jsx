import React, { useState } from 'react'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { Play, Settings, TrendingUp, Users, Skull, Heart } from 'lucide-react'
import { simulationService } from '../services/api.js'

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'white', border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '10px 14px', boxShadow: 'var(--shadow-md)',
      fontSize: 12
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>Day {label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color, display: 'flex', gap: 12, justifyContent: 'space-between', marginBottom: 2 }}>
          <span>{p.name}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

const INTERVENTIONS = [
  { id: 'no_action', label: 'No Intervention', desc: 'Natural epidemic progression' },
  { id: 'partial_lockdown', label: 'Partial Lockdown', desc: 'Restrict movement by 40%' },
  { id: 'full_lockdown', label: 'Full Lockdown', desc: 'Complete movement restriction' },
  { id: 'vaccination_rollout', label: 'Vaccination Rollout', desc: 'Accelerated vaccination campaign' },
  { id: 'combined_strategy', label: 'Combined Strategy', desc: 'Lockdown + vaccination + surveillance' },
  { id: 'school_closure', label: 'School Closures', desc: 'Close all educational institutions' },
  { id: 'travel_restriction', label: 'Travel Restrictions', desc: 'Restrict inter-zone movement' },
]

export default function SimulationPage({ regionId }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [config, setConfig] = useState({
    intervention: 'no_action',
    days: 180,
  })

  const runSimulation = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await simulationService.run({
        region_id: regionId,
        days: config.days,
        intervention: config.intervention
      })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Simulation failed. Ensure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const timeline = result?.simulation_result?.timeline || []
  // Sample every N days to keep chart responsive
  const step = Math.max(1, Math.floor(timeline.length / 90))
  const chartData = timeline.filter((_, i) => i % step === 0).map(d => ({
    day: d.day,
    Susceptible: d.susceptible,
    Exposed: d.exposed,
    Infected: d.infected,
    Recovered: d.recovered,
    Deceased: d.deceased,
  }))

  const sim = result?.simulation_result || {}

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">SEIR Simulation Engine</h1>
        <p className="page-subtitle">Configure and run the epidemiological model for {regionId}</p>
      </div>

      {/* Config panel */}
      <div className="chart-card" style={{ marginBottom: 20 }}>
        <div className="chart-card-header">
          <div className="chart-card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Settings size={15} /> Simulation Configuration
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 16, alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 6 }}>
              Intervention Strategy
            </label>
            <select
              value={config.intervention}
              onChange={e => setConfig(c => ({ ...c, intervention: e.target.value }))}
            >
              {INTERVENTIONS.map(iv => (
                <option key={iv.id} value={iv.id}>{iv.label} — {iv.desc}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 6 }}>
              Simulation Duration (Days)
            </label>
            <select value={config.days} onChange={e => setConfig(c => ({ ...c, days: +e.target.value }))}>
              <option value={90}>90 Days</option>
              <option value={180}>180 Days</option>
              <option value={270}>270 Days</option>
              <option value={365}>365 Days</option>
            </select>
          </div>

          <button className="btn btn-primary" onClick={runSimulation} disabled={loading} style={{ height: 36, paddingLeft: 20, paddingRight: 20 }}>
            {loading ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Running...</> : <><Play size={14} /> Run Simulation</>}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!result && !loading && (
        <div style={{
          background: 'var(--color-surface)', border: '1px dashed var(--color-border)',
          borderRadius: 'var(--radius-lg)', padding: '60px 24px', textAlign: 'center',
          color: 'var(--color-text-muted)'
        }}>
          <Play size={32} style={{ margin: '0 auto 12px', opacity: 0.3, display: 'block' }} />
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Ready to Simulate</div>
          <div style={{ fontSize: 13 }}>Select an intervention and click Run Simulation</div>
        </div>
      )}

      {result && (
        <>
          {/* Result metrics */}
          <div className="grid-4" style={{ marginBottom: 20 }}>
            <div className="stat-card" style={{ borderTop: '3px solid var(--color-accent)' }}>
              <div className="stat-label">R0 (Basic Reproduction)</div>
              <div className="stat-value">{sim.r0}</div>
            </div>
            <div className="stat-card" style={{ borderTop: '3px solid var(--color-critical)' }}>
              <div className="stat-label">Peak Infected</div>
              <div className="stat-value">{fmt(sim.peak_infected)}</div>
              <div className="stat-delta">Day {sim.peak_day}</div>
            </div>
            <div className="stat-card" style={{ borderTop: '3px solid var(--color-high)' }}>
              <div className="stat-label">Total Infected</div>
              <div className="stat-value">{fmt(sim.total_infected)}</div>
            </div>
            <div className="stat-card" style={{ borderTop: '3px solid var(--color-text-muted)' }}>
              <div className="stat-label">Total Deceased</div>
              <div className="stat-value">{fmt(sim.total_deceased)}</div>
              <div className="stat-delta">{sim.epidemic_end_day ? `Ends ~Day ${sim.epidemic_end_day}` : 'Ongoing'}</div>
            </div>
          </div>

          {/* SEIR Curve */}
          <div className="chart-card" style={{ marginBottom: 20 }}>
            <div className="chart-card-header">
              <div>
                <div className="chart-card-title">SEIR Compartment Model</div>
                <div className="chart-card-sub">Intervention: {INTERVENTIONS.find(i => i.id === config.intervention)?.label} — {config.days} day simulation</div>
              </div>
              <span className="badge badge-info">{sim.scenario_name?.replace('_', ' ').toUpperCase()}</span>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} label={{ value: 'Days', position: 'insideBottom', offset: -2, fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} tickFormatter={fmt} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {sim.peak_day && <ReferenceLine x={sim.peak_day} stroke="var(--color-critical)" strokeDasharray="4 4" label={{ value: 'Peak', fontSize: 10, fill: 'var(--color-critical)' }} />}
                <Line type="monotone" dataKey="Susceptible" stroke="#1a56db" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Exposed" stroke="#f39c12" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="Infected" stroke="#e74c3c" strokeWidth={2.5} dot={false} />
                <Line type="monotone" dataKey="Recovered" stroke="#27ae60" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Deceased" stroke="#8896a4" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Active cases area */}
          <div className="chart-card">
            <div className="chart-card-header">
              <div>
                <div className="chart-card-title">Active Infection Curve</div>
                <div className="chart-card-sub">Concurrent infections over time — identifies healthcare system stress</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="infGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e74c3c" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#e74c3c" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} tickFormatter={fmt} />
                <Tooltip content={<CustomTooltip />} />
                {sim.peak_day && <ReferenceLine x={sim.peak_day} stroke="var(--color-critical)" strokeDasharray="4 4" />}
                <Area type="monotone" dataKey="Infected" stroke="#e74c3c" fill="url(#infGrad)" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
