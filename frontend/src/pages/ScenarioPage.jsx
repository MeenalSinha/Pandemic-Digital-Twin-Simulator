import React, { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts'
import { BarChart3, Play, CheckCircle, TrendingDown } from 'lucide-react'
import { scenarioService } from '../services/api.js'

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

const SCENARIO_COLORS = {
  no_action: '#e74c3c',
  partial_lockdown: '#f39c12',
  full_lockdown: '#27ae60',
  vaccination_rollout: '#1a56db',
  combined_strategy: '#8e44ad',
  school_closure: '#16a085',
  travel_restriction: '#d35400',
}

const SCENARIO_LABELS = {
  no_action: 'No Intervention',
  partial_lockdown: 'Partial Lockdown',
  full_lockdown: 'Full Lockdown',
  vaccination_rollout: 'Vaccination Rollout',
  combined_strategy: 'Combined Strategy',
  school_closure: 'School Closures',
  travel_restriction: 'Travel Restrictions',
}

const AVAILABLE = ['no_action', 'partial_lockdown', 'full_lockdown', 'vaccination_rollout', 'combined_strategy']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'white', border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '10px 14px', boxShadow: 'var(--shadow-md)', fontSize: 12
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

export default function ScenarioPage({ regionId }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(new Set(AVAILABLE))
  const [days, setDays] = useState(180)

  const toggle = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) { if (next.size > 1) next.delete(id) }
      else next.add(id)
      return next
    })
  }

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await scenarioService.run({
        region_id: regionId,
        days,
        interventions: Array.from(selected)
      })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Scenario run failed.')
    } finally {
      setLoading(false)
    }
  }

  // Build combined timeline for chart
  let combinedTimeline = []
  if (result?.scenarios) {
    const scenarios = result.scenarios
    const anyTimeline = Object.values(scenarios)[0]?.timeline || []
    const step = Math.max(1, Math.floor(anyTimeline.length / 60))
    combinedTimeline = anyTimeline
      .filter((_, i) => i % step === 0)
      .map(d => {
        const row = { day: d.day }
        for (const [name, sc] of Object.entries(scenarios)) {
          const match = sc.timeline?.find(t => t.day === d.day)
          if (match) row[SCENARIO_LABELS[name] || name] = match.infected
        }
        return row
      })
  }

  const comparisons = result?.comparisons || []
  const best = result?.best_scenario

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">What-If Scenario Analysis</h1>
        <p className="page-subtitle">Compare intervention outcomes side-by-side to identify optimal strategies</p>
      </div>

      {/* Config */}
      <div className="chart-card" style={{ marginBottom: 20 }}>
        <div className="chart-card-title" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <BarChart3 size={15} /> Scenario Configuration
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: 8 }}>
            Select Interventions to Compare
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {AVAILABLE.map(id => (
              <button
                key={id}
                onClick={() => toggle(id)}
                className={`btn ${selected.has(id) ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: 12, padding: '5px 12px' }}
              >
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: SCENARIO_COLORS[id], display: 'inline-block' }} />
                {SCENARIO_LABELS[id]}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 180 }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: 6 }}>
              Duration
            </div>
            <select value={days} onChange={e => setDays(+e.target.value)}>
              <option value={90}>90 Days</option>
              <option value={180}>180 Days</option>
              <option value={365}>365 Days</option>
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={run}
            disabled={loading}
            style={{ marginTop: 18, paddingLeft: 24, paddingRight: 24 }}
          >
            {loading
              ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Running...</>
              : <><Play size={14} /> Run All Scenarios</>
            }
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
          <BarChart3 size={32} style={{ margin: '0 auto 12px', opacity: 0.3, display: 'block' }} />
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Select Interventions and Run</div>
          <div style={{ fontSize: 13 }}>All selected scenarios will be simulated simultaneously</div>
        </div>
      )}

      {result && (
        <>
          {/* Best scenario highlight */}
          {best && (
            <div style={{
              background: 'var(--color-low-light)', border: '1px solid #a8d5b8',
              borderRadius: 'var(--radius-lg)', padding: '14px 18px', marginBottom: 20,
              display: 'flex', alignItems: 'center', gap: 12
            }}>
              <CheckCircle size={18} color="var(--color-low)" />
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-low)' }}>
                  Best Outcome: {SCENARIO_LABELS[best.scenario]}
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                  Reduces total infections by {best.reduction_vs_baseline_pct}% — saves approximately {fmt(best.lives_saved)} lives vs no intervention
                </div>
              </div>
              {result.agent_reasoning && (
                <div style={{ marginLeft: 'auto', maxWidth: 300, fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                  {result.agent_reasoning}
                </div>
              )}
            </div>
          )}

          {/* Comparison chart */}
          <div className="chart-card" style={{ marginBottom: 20 }}>
            <div className="chart-card-header">
              <div>
                <div className="chart-card-title">Active Cases by Intervention</div>
                <div className="chart-card-sub">Concurrent infections over simulation period</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={combinedTimeline} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} tickFormatter={fmt} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {Object.keys(result.scenarios || {}).map(name => (
                  <Line
                    key={name}
                    type="monotone"
                    dataKey={SCENARIO_LABELS[name] || name}
                    stroke={SCENARIO_COLORS[name] || '#ccc'}
                    strokeWidth={name === 'no_action' ? 2.5 : 2}
                    strokeDasharray={name === 'no_action' ? '6 3' : undefined}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Comparison table */}
          <div className="chart-card" style={{ marginBottom: 20 }}>
            <div className="chart-card-header">
              <div>
                <div className="chart-card-title">Outcome Comparison Table</div>
                <div className="chart-card-sub">Sorted by total infections (ascending)</div>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                    {['Rank', 'Scenario', 'Total Infected', 'Peak Cases', 'Peak Day', 'Deaths', 'Reduction vs Baseline', 'Lives Saved'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comparisons.map((row, i) => (
                    <tr key={row.scenario} style={{
                      borderBottom: '1px solid var(--color-border)',
                      background: i === 0 ? 'var(--color-low-light)' : 'transparent'
                    }}>
                      <td style={{ padding: '10px 12px', fontWeight: 700, color: i === 0 ? 'var(--color-low)' : 'var(--color-text-muted)' }}>
                        #{i + 1}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ width: 10, height: 10, borderRadius: '50%', background: SCENARIO_COLORS[row.scenario], flexShrink: 0 }} />
                          <span style={{ fontWeight: 600 }}>{row.display_name}</span>
                          {i === 0 && <span className="badge badge-low">Best</span>}
                        </div>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{fmt(row.total_infected)}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>{fmt(row.peak_infected)}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>{row.peak_day}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--color-critical)' }}>{fmt(row.total_deceased)}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 60, height: 6, background: 'var(--color-surface-2)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${Math.max(0, row.reduction_vs_baseline_pct)}%`, height: '100%', background: 'var(--color-low)', borderRadius: 3 }} />
                          </div>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: row.reduction_vs_baseline_pct > 0 ? 'var(--color-low)' : 'var(--color-text-muted)' }}>
                            {row.reduction_vs_baseline_pct > 0 ? `-${row.reduction_vs_baseline_pct}%` : 'Baseline'}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: row.lives_saved > 0 ? 'var(--color-low)' : 'var(--color-text-muted)' }}>
                        {row.lives_saved > 0 ? `+${fmt(row.lives_saved)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bar chart comparison */}
          <div className="chart-card">
            <div className="chart-card-header">
              <div className="chart-card-title">Peak Infections Comparison</div>
              <div className="chart-card-sub">Maximum concurrent infections by scenario</div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={comparisons} margin={{ top: 5, right: 10, left: 0, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  dataKey="display_name"
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  angle={-20} textAnchor="end"
                />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} tickFormatter={fmt} />
                <Tooltip formatter={(val) => [fmt(val), 'Peak Infected']} />
                <Bar dataKey="peak_infected" radius={[4, 4, 0, 0]}>
                  {comparisons.map((entry, i) => (
                    <Cell key={`cell-${i}`} fill={SCENARIO_COLORS[entry.scenario] || '#ccc'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
