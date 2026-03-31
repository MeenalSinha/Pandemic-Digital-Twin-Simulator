import React, { useState, useEffect, useRef } from 'react'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell
} from 'recharts'
import { scenarioService, regionService } from '../services/api.js'

const fmt = n => {
  if (n === null || n === undefined) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'K'
  return Math.round(n).toLocaleString()
}

const fmtMoney = n => {
  if (!n) return '$—'
  if (n >= 1e9) return '$' + (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return '$' + (n / 1e6).toFixed(0) + 'M'
  return '$' + Math.round(n).toLocaleString()
}

const SCENARIO_META = {
  no_action:           { label: 'No Intervention',   color: '#c0392b', dash: '6 3' },
  partial_lockdown:    { label: 'Partial Lockdown',  color: '#e67e22', dash: null },
  full_lockdown:       { label: 'Full Lockdown',     color: '#27ae60', dash: null },
  vaccination_rollout: { label: 'Vaccination',       color: '#2980b9', dash: null },
  combined_strategy:   { label: 'Combined Strategy', color: '#8e44ad', dash: null },
}

// ── Animated counter ─────────────────────────────────────────────────────────
function Counter({ target, duration = 1200, prefix = '', suffix = '', color }) {
  const [val, setVal] = useState(0)
  const raf = useRef(null)
  useEffect(() => {
    if (!target) return
    const start = performance.now()
    const step = (now) => {
      const p = Math.min(1, (now - start) / duration)
      const ease = 1 - Math.pow(1 - p, 3)
      setVal(Math.round(ease * target))
      if (p < 1) raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])
  return <span style={{ color }}>{prefix}{fmt(val)}{suffix}</span>
}

// ── Custom tooltip ────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'white', border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '10px 14px', boxShadow: 'var(--shadow-md)', fontSize: 12
    }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>Day {label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color, display: 'flex', gap: 12, justifyContent: 'space-between', marginBottom: 2 }}>
          <span>{p.name}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ── Step indicator ────────────────────────────────────────────────────────────
function Step({ n, label, active, done }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%',
        background: done ? 'var(--color-low)' : active ? 'var(--color-accent)' : 'var(--color-surface-2)',
        color: done || active ? 'white' : 'var(--color-text-muted)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700, flexShrink: 0,
        transition: 'all 0.3s',
      }}>{done ? '✓' : n}</div>
      <span style={{
        fontSize: 13, fontWeight: active ? 700 : 500,
        color: active ? 'var(--color-text-primary)' : done ? 'var(--color-low)' : 'var(--color-text-muted)',
        transition: 'all 0.3s',
      }}>{label}</span>
    </div>
  )
}

export default function DemoPage({ regionId }) {
  const [step, setStep] = useState(0)        // 0=idle 1=loading 2=baseline 3=comparing 4=wow 5=economics
  const [regionData, setRegionData] = useState(null)
  const [scenarios, setScenarios] = useState(null)
  const [error, setError] = useState(null)

  const region = regionData?.region

  const runDemo = async () => {
    setStep(1)
    setError(null)
    try {
      const [rd, sc] = await Promise.all([
        regionService.getById(regionId),
        scenarioService.run({
          region_id: regionId, days: 180,
          interventions: ['no_action','partial_lockdown','full_lockdown','vaccination_rollout','combined_strategy']
        })
      ])
      setRegionData(rd)
      setScenarios(sc)
      setStep(2)
      setTimeout(() => setStep(3), 800)
      setTimeout(() => setStep(4), 1800)
      setTimeout(() => setStep(5), 3000)
    } catch (e) {
      setError(e.friendlyMessage || 'Demo failed. Is the backend running on port 8000?')
      setStep(0)
    }
  }

  const reset = () => { setStep(0); setScenarios(null); setRegionData(null) }

  // Build chart data
  const buildChartData = () => {
    if (!scenarios?.scenarios) return []
    const base = scenarios.scenarios.no_action?.timeline || []
    const step = Math.max(1, Math.floor(base.length / 60))
    return base.filter((_, i) => i % step === 0).map(d => {
      const row = { day: d.day }
      for (const [iv, sc] of Object.entries(scenarios.scenarios)) {
        const match = sc.timeline?.find(t => t.day === d.day)
        row[SCENARIO_META[iv]?.label || iv] = match?.infected || 0
      }
      return row
    })
  }

  const chartData = buildChartData()
  const baseline = scenarios?.comparisons?.find(c => c.scenario === 'no_action')
  const best = scenarios?.best_scenario
  const bestMeta = best ? SCENARIO_META[best.scenario] : null

  // WOW numbers
  const baselineInfected = baseline?.total_infected || 0
  const bestInfected     = best?.total_infected || 0
  const livesaved        = best?.lives_saved || 0
  const reductionPct     = best?.reduction_vs_baseline_pct || 0
  const baselineDeaths   = baseline?.total_deceased || 0
  const bestDeaths       = best?.total_deceased || 0

  return (
    <div className="fade-in" style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px 28px',
        marginBottom: 20,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
              Pandemic Digital Twin
            </h1>
            <p style={{ fontSize: 13, color: 'var(--color-text-muted)', maxWidth: 520 }}>
              AI-powered epidemic simulation. Watch a real SEIR model run across 5 intervention
              strategies simultaneously — then see the human cost difference in real numbers.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {step > 0 && (
              <button className="btn btn-secondary" onClick={reset} style={{ fontSize: 12 }}>
                Reset
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={runDemo}
              disabled={step === 1}
              style={{ fontSize: 14, padding: '10px 24px', fontWeight: 700 }}
            >
              {step === 0 ? 'Run Demo' : step === 1 ? (
                <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Simulating...</>
              ) : 'Re-run Demo'}
            </button>
          </div>
        </div>

        {/* Step progress */}
        {step > 0 && (
          <div style={{
            marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--color-border)',
            display: 'flex', gap: 24, flexWrap: 'wrap'
          }}>
            <Step n={1} label="Loading real data" active={step === 1} done={step > 1} />
            <Step n={2} label="Running SEIR model (5 scenarios)" active={step === 2} done={step > 2} />
            <Step n={3} label="Comparing outcomes" active={step === 3} done={step > 3} />
            <Step n={4} label="WOW moment" active={step === 4} done={step > 4} />
            <Step n={5} label="Policy recommendation" active={step === 5} done={step > 5} />
          </div>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Idle state */}
      {step === 0 && (
        <div style={{
          background: 'var(--color-surface)', border: '2px dashed var(--color-border)',
          borderRadius: 'var(--radius-lg)', padding: '60px 24px', textAlign: 'center',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>△</div>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Press "Run Demo" to Begin</div>
          <div style={{ fontSize: 13, color: 'var(--color-text-muted)', maxWidth: 480, margin: '0 auto', lineHeight: 1.7 }}>
            The system will load real population data for {regionId}, run 5 simultaneous
            SEIR simulations across different intervention strategies, and compute the
            exact human cost difference between action and inaction.
          </div>
        </div>
      )}

      {/* Loading */}
      {step === 1 && (
        <div className="loading-container">
          <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
          <div style={{ fontSize: 15, fontWeight: 600 }}>Running 5 SEIR simulations simultaneously...</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
            scipy.integrate.odeint solving differential equations across 180-day windows
          </div>
        </div>
      )}

      {/* Results visible */}
      {step >= 2 && scenarios && (
        <>
          {/* WOW MOMENT — the killer panel */}
          {step >= 4 && best && baseline && (
            <div style={{
              background: 'linear-gradient(135deg, #0a2540 0%, #0d3a6e 100%)',
              border: '2px solid #1a56db',
              borderRadius: 'var(--radius-lg)',
              padding: '28px 32px',
              marginBottom: 20,
              color: 'white',
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#7eb8f7', marginBottom: 16 }}>
                The Decision That Changes Everything
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 20, alignItems: 'center', marginBottom: 24 }}>
                {/* No intervention column */}
                <div style={{ background: 'rgba(192,57,43,0.15)', borderRadius: 10, padding: '18px 20px', border: '1px solid rgba(192,57,43,0.3)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#e57373', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10 }}>
                    No Intervention
                  </div>
                  <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#ff6b6b', letterSpacing: '-0.02em', lineHeight: 1 }}>
                    <Counter target={baselineInfected} duration={1000} color="#ff6b6b" />
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4 }}>total infected</div>
                  <div style={{ marginTop: 10, fontSize: 13, color: '#ff9999' }}>
                    <Counter target={baselineDeaths} duration={1100} color="#ff9999" /> deaths
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                    Peak day {baseline?.peak_day}: <Counter target={baseline?.peak_infected} duration={1000} color="rgba(255,255,255,0.6)" /> simultaneous
                  </div>
                </div>

                {/* Arrow */}
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 28, color: '#7eb8f7', lineHeight: 1 }}>→</div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>{bestMeta?.label}</div>
                </div>

                {/* Best intervention column */}
                <div style={{ background: 'rgba(39,174,96,0.15)', borderRadius: 10, padding: '18px 20px', border: '1px solid rgba(39,174,96,0.3)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#69d98c', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10 }}>
                    {bestMeta?.label}
                  </div>
                  <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#69d98c', letterSpacing: '-0.02em', lineHeight: 1 }}>
                    <Counter target={bestInfected} duration={1200} color="#69d98c" />
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 4 }}>total infected</div>
                  <div style={{ marginTop: 10, fontSize: 13, color: '#a8f0be' }}>
                    <Counter target={bestDeaths} duration={1300} color="#a8f0be" /> deaths
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                    Peak day {best?.peak_day}: <Counter target={best?.peak_infected} duration={1200} color="rgba(255,255,255,0.6)" /> simultaneous
                  </div>
                </div>
              </div>

              {/* The killer numbers */}
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12,
                borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 20
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#69d98c', lineHeight: 1 }}>
                    -{reductionPct}%
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>infection reduction</div>
                </div>
                <div style={{ textAlign: 'center', borderLeft: '1px solid rgba(255,255,255,0.1)', borderRight: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: 32, fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#7eb8f7', lineHeight: 1 }}>
                    <Counter target={livesaved} duration={1400} color="#7eb8f7" />
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>lives saved</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#ffd166', lineHeight: 1 }}>
                    +{best?.peak_day - (baseline?.peak_day || 0)} days
                  </div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>peak delayed</div>
                </div>
              </div>
            </div>
          )}

          {/* Comparison chart */}
          <div className="chart-card" style={{ marginBottom: 16 }}>
            <div className="chart-card-header">
              <div>
                <div className="chart-card-title">Active Infections — All 5 Strategies (180 Days)</div>
                <div className="chart-card-sub">
                  {regionData?.region?.name} — {regionData?.region?.population?.toLocaleString()} population
                  — Each line is a live SEIR ODE simulation
                </div>
              </div>
              {step >= 3 && (
                <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {scenarios?.comparisons?.length} scenarios computed
                </span>
              )}
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                  label={{ value: 'Days', position: 'insideBottom', offset: -2, fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} tickFormatter={fmt} />
                <Tooltip content={<CustomTooltip />} />
                {baseline?.peak_day && (
                  <ReferenceLine x={baseline.peak_day} stroke="var(--color-critical)"
                    strokeDasharray="3 3"
                    label={{ value: 'No-action peak', fontSize: 9, fill: 'var(--color-critical)', position: 'top' }} />
                )}
                {Object.entries(SCENARIO_META).map(([key, meta]) =>
                  scenarios?.scenarios?.[key] ? (
                    <Line key={key} type="monotone" dataKey={meta.label}
                      stroke={meta.color}
                      strokeWidth={key === 'no_action' ? 2.5 : 2}
                      strokeDasharray={meta.dash || undefined}
                      dot={false}
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Comparison table + policy recommendation side by side */}
          {step >= 5 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              {/* Ranked outcomes */}
              <div className="chart-card">
                <div className="chart-card-header">
                  <div className="chart-card-title">Scenario Rankings</div>
                  <div className="chart-card-sub">Sorted by total infections (best first)</div>
                </div>
                <div>
                  {scenarios?.comparisons?.map((row, i) => {
                    const meta = SCENARIO_META[row.scenario] || {}
                    return (
                      <div key={row.scenario} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '9px 0',
                        borderBottom: i < scenarios.comparisons.length - 1 ? '1px solid var(--color-border)' : 'none',
                        background: i === 0 ? 'var(--color-low-light)' : 'transparent',
                        borderRadius: i === 0 ? 6 : 0,
                        paddingLeft: i === 0 ? 8 : 0,
                        paddingRight: i === 0 ? 8 : 0,
                      }}>
                        <div style={{
                          width: 10, height: 10, borderRadius: '50%',
                          background: meta.color, flexShrink: 0
                        }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {row.display_name}
                            {i === 0 && <span className="badge badge-low" style={{ marginLeft: 6 }}>Best</span>}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                            {fmt(row.total_infected)} infected · {fmt(row.lives_saved)} lives saved
                          </div>
                        </div>
                        <div style={{
                          fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 700,
                          color: row.reduction_vs_baseline_pct > 0 ? 'var(--color-low)' : 'var(--color-text-muted)',
                          textAlign: 'right', minWidth: 48
                        }}>
                          {row.reduction_vs_baseline_pct > 0 ? `-${row.reduction_vs_baseline_pct}%` : 'base'}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* AI verdict */}
              <div className="chart-card">
                <div className="chart-card-header">
                  <div className="chart-card-title">AI System Verdict</div>
                  <div className="chart-card-sub">Policy Recommendation Agent + RAG evidence</div>
                </div>

                {best && bestMeta && (
                  <>
                    <div style={{
                      background: 'var(--color-accent-light)', border: '1px solid #c7d8f8',
                      borderRadius: 8, padding: '14px 16px', marginBottom: 14
                    }}>
                      <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--color-accent)', marginBottom: 6 }}>
                        Implement {bestMeta.label}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                        A {bestMeta.label.toLowerCase()} reduces total infections by{' '}
                        <strong style={{ color: 'var(--color-low)' }}>{reductionPct}%</strong> and saves approximately{' '}
                        <strong style={{ color: 'var(--color-accent)' }}>{fmt(livesaved)} lives</strong>{' '}
                        compared to no intervention. The epidemic peak is delayed by{' '}
                        <strong>{best?.peak_day - (baseline?.peak_day || 0)} days</strong>,
                        giving healthcare systems critical preparation time.
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                      {[
                        { label: 'Peak reduction', value: `${Math.round((1 - best.peak_infected / Math.max(1, baseline?.peak_infected)) * 100)}%`, color: 'var(--color-low)' },
                        { label: 'Deaths prevented', value: fmt(baselineDeaths - bestDeaths), color: 'var(--color-accent)' },
                        { label: 'Epidemic ends', value: best.epidemic_end_day ? `Day ${best.epidemic_end_day}` : 'Extended', color: 'var(--color-text-secondary)' },
                        { label: 'Effective R0', value: best.r0?.toFixed(2), color: best.r0 < 1 ? 'var(--color-low)' : 'var(--color-high)' },
                      ].map(({ label, value, color }) => (
                        <div key={label} style={{
                          background: 'var(--color-surface-2)', borderRadius: 8, padding: '10px 12px'
                        }}>
                          <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
                          <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-mono)', color }}>{value}</div>
                        </div>
                      ))}
                    </div>

                    {/* RAG note */}
                    {scenarios?.rag_evidence?.length > 0 && (
                      <div style={{
                        marginTop: 12, padding: '8px 12px', background: 'var(--color-surface-2)',
                        borderRadius: 6, fontSize: 11, color: 'var(--color-text-muted)', borderLeft: '3px solid var(--color-accent)'
                      }}>
                        Evidence grounded in: {scenarios.rag_evidence.slice(0, 2).map(e => e.title).join(' · ')}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
