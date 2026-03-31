import React, { useState } from 'react'
import { Cpu, Play, CheckCircle, AlertTriangle, Clock, TrendingUp, Shield, Target, Activity } from 'lucide-react'
import { agentService } from '../services/api.js'

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

const AGENT_META = {
  prediction: { label: 'Prediction Agent', icon: TrendingUp, color: '#1a56db' },
  risk: { label: 'Risk Analysis Agent', icon: AlertTriangle, color: '#d35400' },
  policy: { label: 'Policy Recommendation Agent', icon: Shield, color: '#8e44ad' },
  simulation: { label: 'Simulation Agent', icon: Activity, color: '#27ae60' },
}

function AgentCard({ name, agent }) {
  const meta = AGENT_META[name] || {}
  const Icon = meta.icon || Cpu
  const isComplete = agent.status === 'completed'
  const isError = agent.status === 'error'

  return (
    <div className="chart-card" style={{
      borderLeft: `4px solid ${meta.color || 'var(--color-border)'}`,
      opacity: isError ? 0.7 : 1
    }}>
      {/* Agent header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8,
            background: meta.color ? meta.color + '18' : 'var(--color-surface-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Icon size={16} color={meta.color || 'var(--color-text-muted)'} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {meta.label || name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              {agent.execution_time ? `${agent.execution_time}s` : '—'} execution
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isComplete && <CheckCircle size={15} color="var(--color-low)" />}
          {isError && <AlertTriangle size={15} color="var(--color-critical)" />}
          <span className="badge badge-info">
            {Math.round((agent.confidence || 0) * 100)}% confidence
          </span>
        </div>
      </div>

      {/* Reasoning */}
      {agent.reasoning && (
        <div style={{
          background: 'var(--color-surface-2)', borderRadius: 6,
          padding: '10px 12px', marginBottom: 12, fontSize: 12,
          color: 'var(--color-text-secondary)', lineHeight: 1.6,
          borderLeft: '3px solid var(--color-border-strong)'
        }}>
          {agent.reasoning}
        </div>
      )}

      {/* Key output metrics */}
      {agent.output && !agent.output.error && (
        <AgentOutputMetrics name={name} output={agent.output} color={meta.color} />
      )}

      {/* Recommendations */}
      {agent.recommendations?.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: 6 }}>
            Agent Recommendations
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {agent.recommendations.map((rec, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <div style={{
                  width: 16, height: 16, borderRadius: 4, background: meta.color + '20',
                  color: meta.color, fontSize: 9, fontWeight: 700, display: 'flex',
                  alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1
                }}>{i + 1}</div>
                <span style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AgentOutputMetrics({ name, output, color }) {
  if (name === 'prediction') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {[
          { label: 'R0', value: output.r0 },
          { label: 'Peak Cases', value: fmt(output.peak_infected) },
          { label: 'Attack Rate', value: `${output.attack_rate_pct}%` },
          { label: 'Peak Day', value: `Day ${output.peak_day}` },
          { label: 'Severity', value: output.severity_level },
          { label: 'Trend', value: output.trend_direction },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: 'var(--color-surface-2)', borderRadius: 6, padding: '8px 10px' }}>
            <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>{value || '—'}</div>
          </div>
        ))}
      </div>
    )
  }

  if (name === 'risk') {
    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 10 }}>
          {[
            { label: 'Critical Zones', value: output.risk_distribution?.CRITICAL || 0, color: 'var(--color-critical)' },
            { label: 'High Risk', value: output.risk_distribution?.HIGH || 0, color: 'var(--color-high)' },
            { label: 'Moderate', value: output.risk_distribution?.MODERATE || 0, color: 'var(--color-moderate)' },
            { label: 'Low Risk', value: output.risk_distribution?.LOW || 0, color: 'var(--color-low)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: 'var(--color-surface-2)', borderRadius: 6, padding: '8px 10px', textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>{value}</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>
        {output.alerts?.map((alert, i) => (
          <div key={i} style={{
            display: 'flex', gap: 8, alignItems: 'center', padding: '6px 10px',
            background: alert.level === 'CRITICAL' ? 'var(--color-critical-light)' : 'var(--color-high-light)',
            borderRadius: 6, marginBottom: 4, fontSize: 11
          }}>
            <AlertTriangle size={12} color={alert.level === 'CRITICAL' ? 'var(--color-critical)' : 'var(--color-high)'} />
            <span style={{ color: alert.level === 'CRITICAL' ? 'var(--color-critical)' : 'var(--color-high)' }}>
              <strong>{alert.zone}:</strong> {alert.message}
            </span>
          </div>
        ))}
      </div>
    )
  }

  if (name === 'policy') {
    const primary = output.primary_recommendation
    return (
      <div>
        {primary && (
          <div style={{
            background: 'var(--color-accent-light)', border: '1px solid #c7d8f8',
            borderRadius: 8, padding: '12px 14px', marginBottom: 10
          }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-accent)', marginBottom: 4 }}>
              Recommended: {primary.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginBottom: 8 }}>
              {primary.description}
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              <span style={{ fontSize: 11 }}>Effectiveness: <strong style={{ color: 'var(--color-low)' }}>{Math.round((primary.effectiveness || 0) * 100)}%</strong></span>
              <span style={{ fontSize: 11 }}>Econ Cost: <strong style={{ color: 'var(--color-high)' }}>{Math.round((primary.economic_cost || 0) * 100)}%</strong></span>
              <span style={{ fontSize: 11 }}>Duration: <strong>{primary.duration_weeks}w</strong></span>
            </div>
          </div>
        )}
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: 6 }}>
          All Ranked Policies
        </div>
        {output.ranked_policies?.slice(0, 4).map((p, i) => (
          <div key={p.id} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '6px 0', borderBottom: i < 3 ? '1px solid var(--color-border)' : 'none',
            fontSize: 12
          }}>
            <span style={{ color: 'var(--color-text-secondary)' }}>#{i + 1} {p.name}</span>
            <div style={{ display: 'flex', gap: 10 }}>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-low)' }}>{p.composite_score}</span>
              {p.recommended && <span className="badge badge-low">Best</span>}
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (name === 'simulation') {
    const best = output.best_scenario
    return (
      <div>
        {best && (
          <div style={{ background: 'var(--color-low-light)', borderRadius: 8, padding: '10px 14px', marginBottom: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-low)' }}>
              Best Scenario: {best.scenario?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 3 }}>
              {best.reduction_vs_baseline}% infection reduction — {fmt(best.lives_saved)} lives saved
            </div>
          </div>
        )}
        {output.what_if_insights?.map((insight, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, fontSize: 12 }}>
            <Target size={13} color={color} style={{ marginTop: 1, flexShrink: 0 }} />
            <div>
              <strong>{insight.scenario?.replace(/_/g, ' ')}:</strong>{' '}
              <span style={{ color: 'var(--color-text-secondary)' }}>{insight.key_finding}</span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return null
}

export default function AgentsPage({ regionId }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await agentService.analyze({
        region_id: regionId,
        days: 180,
        intervention: 'no_action',
        run_all_scenarios: true
      })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Agent analysis failed. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const agents = result?.analysis?.agents || {}
  const synthesis = result?.analysis?.synthesis || {}
  const totalTime = result?.analysis?.total_execution_time

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Multi-Agent AI System</h1>
          <p className="page-subtitle">
            Four specialized agents collaborate to analyze, predict, and recommend pandemic interventions
          </p>
        </div>
        <button className="btn btn-primary" onClick={run} disabled={loading} style={{ paddingLeft: 20, paddingRight: 20 }}>
          {loading
            ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Orchestrating agents...</>
            : <><Cpu size={14} /> Run Agent Analysis</>
          }
        </button>
      </div>

      {/* Architecture overview */}
      <div className="chart-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'var(--color-border)' }}>
          {Object.entries(AGENT_META).map(([key, meta]) => {
            const Icon = meta.icon
            const agentData = agents[key]
            const isComplete = agentData?.status === 'completed'
            return (
              <div key={key} style={{ background: 'var(--color-surface)', padding: '14px 16px', textAlign: 'center' }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, margin: '0 auto 8px',
                  background: meta.color + '15', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: isComplete ? `2px solid ${meta.color}` : '2px solid var(--color-border)'
                }}>
                  <Icon size={18} color={meta.color} />
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 2 }}>{meta.label}</div>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                  {isComplete ? `${agentData.execution_time}s` : 'Pending'}
                </div>
                {isComplete && (
                  <div style={{ marginTop: 6 }}>
                    <CheckCircle size={13} color="var(--color-low)" style={{ margin: '0 auto' }} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {totalTime && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
            borderTop: '1px solid var(--color-border)', fontSize: 11, color: 'var(--color-text-muted)'
          }}>
            <Clock size={12} />
            Total orchestration time: <strong style={{ fontFamily: 'var(--font-mono)' }}>{totalTime}s</strong>
            <span style={{ marginLeft: 8 }}>Communication pattern: Async shared-state pipeline</span>
          </div>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!result && !loading && (
        <div style={{
          background: 'var(--color-surface)', border: '1px dashed var(--color-border)',
          borderRadius: 'var(--radius-lg)', padding: '60px 24px', textAlign: 'center',
          color: 'var(--color-text-muted)'
        }}>
          <Cpu size={36} style={{ margin: '0 auto 12px', opacity: 0.3, display: 'block' }} />
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Launch the Multi-Agent Pipeline</div>
          <div style={{ fontSize: 13 }}>All four agents will run in parallel, sharing outputs for collaborative analysis</div>
        </div>
      )}

      {result && (
        <>
          {/* Synthesis panel */}
          {Object.keys(synthesis).length > 0 && (
            <div style={{
              background: 'var(--color-surface)', border: '2px solid var(--color-accent)',
              borderRadius: 'var(--radius-lg)', padding: '18px 20px', marginBottom: 20
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <Target size={16} color="var(--color-accent)" />
                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-accent)' }}>
                  Multi-Agent Synthesis
                </span>
                <span className={`badge badge-${synthesis.overall_severity?.toLowerCase() === 'critical' ? 'critical' : synthesis.overall_severity?.toLowerCase() === 'high' ? 'high' : 'moderate'}`}>
                  {synthesis.overall_severity}
                </span>
                <span className="badge badge-info">{synthesis.urgency}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 14 }}>
                {[
                  { label: 'R0', val: synthesis.key_metrics?.r0 },
                  { label: 'Peak Cases', val: fmt(synthesis.key_metrics?.peak_infected) },
                  { label: 'Attack Rate', val: `${synthesis.key_metrics?.attack_rate_pct}%` },
                  { label: 'High Risk Zones', val: synthesis.key_metrics?.high_risk_zones },
                ].map(({ label, val }) => (
                  <div key={label} style={{ textAlign: 'center', padding: '10px', background: 'var(--color-accent-light)', borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--color-accent)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{val || '—'}</div>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                  Primary Recommendation: <strong style={{ color: 'var(--color-text-primary)' }}>{synthesis.primary_recommendation}</strong>
                </div>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                  {Object.entries(synthesis.confidence_summary || {}).filter(([k]) => k !== 'overall').map(([agent, conf]) => (
                    <span key={agent} style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                      {agent}: <strong style={{ fontFamily: 'var(--font-mono)' }}>{Math.round(conf * 100)}%</strong>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Individual agent cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {Object.entries(agents).map(([name, agent]) => (
              <AgentCard key={name} name={name} agent={agent} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
