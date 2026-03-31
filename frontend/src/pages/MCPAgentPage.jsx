import React, { useState } from 'react'
import { Bot, Zap, Database, MessageSquare, ChevronRight, Cpu, Play, CheckCircle, AlertCircle } from 'lucide-react'

const EXAMPLE_QUERIES = [
  "What is the impact of a full lockdown in Delhi?",
  "How effective is vaccination rollout in London?",
  "Show me combined strategy results for Tokyo",
  "What happens with no action in New York?",
  "Analyze travel restrictions in Sao Paulo",
  "How much does school closure help in Mumbai?",
]

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

function FlowStep({ number, label, active, done }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
      opacity: active || done ? 1 : 0.4,
      transition: 'opacity 0.3s ease',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: '50%',
        background: done ? 'var(--color-low)' : active ? 'var(--color-accent)' : 'var(--color-surface-2)',
        border: `2px solid ${done ? 'var(--color-low)' : active ? 'var(--color-accent)' : 'var(--color-border)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: done || active ? 'white' : 'var(--color-text-muted)',
        fontSize: 13, fontWeight: 700,
        transition: 'all 0.3s ease',
        boxShadow: active ? '0 0 12px rgba(26,86,219,0.4)' : 'none',
      }}>
        {done ? <CheckCircle size={16} /> : number}
      </div>
      <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textAlign: 'center', maxWidth: 80, lineHeight: 1.3 }}>
        {label}
      </div>
    </div>
  )
}

function DataCard({ label, value, color, sub }) {
  return (
    <div style={{
      background: 'var(--color-surface-2)',
      border: `1px solid ${color}30`,
      borderTop: `3px solid ${color}`,
      borderRadius: 8,
      padding: '12px 14px',
    }}>
      <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', marginBottom: 2 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{sub}</div>}
    </div>
  )
}

export default function MCPAgentPage() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [step, setStep] = useState(0) // 0=idle 1=parsing 2=calling-tool 3=generating 4=done

  const run = async (q) => {
    const queryText = q || query
    if (!queryText.trim()) return

    setLoading(true)
    setResult(null)
    setError(null)
    setStep(1)

    try {
      // Animate steps
      const stepDelay = ms => new Promise(res => setTimeout(res, ms))
      stepDelay(600).then(() => setStep(2))
      stepDelay(1400).then(() => setStep(3))

      const res = await fetch('/mcp-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText }),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'MCP agent request failed')
      }

      const data = await res.json()
      setStep(4)
      setResult(data)
    } catch (e) {
      setError(e.message || 'Request failed. Make sure the backend is running.')
      setStep(0)
    } finally {
      setLoading(false)
    }
  }

  const useExample = (q) => {
    setQuery(q)
    run(q)
  }

  const data = result?.data
  const intent = result?.intent

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Bot size={26} style={{ color: 'var(--color-accent)' }} />
            MCP Agent Demo
          </h1>
          <p className="page-subtitle">
            PandemicMCPAgent — ADK-powered agent using Model Context Protocol to retrieve structured simulation data
          </p>
        </div>
        <div style={{
          display: 'flex', gap: 6, flexWrap: 'wrap',
          fontSize: 11, color: 'var(--color-text-muted)',
        }}>
          {[
            { icon: Bot, label: '1 Agent' },
            { icon: Zap, label: 'MCP Protocol' },
            { icon: Database, label: '1 Tool' },
          ].map(({ icon: Icon, label }) => (
            <div key={label} style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: 'var(--color-surface-2)', borderRadius: 20,
              padding: '4px 10px', border: '1px solid var(--color-border)',
            }}>
              <Icon size={11} color="var(--color-accent)" />
              <span style={{ fontWeight: 600 }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ADK Architecture Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #1a1f35 0%, #1e2a4a 100%)',
        border: '1px solid #2a3a6a',
        borderRadius: 'var(--radius-lg)',
        padding: '16px 20px',
        marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <Cpu size={20} color="#6ca0f8" />
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#c5d8ff', marginBottom: 2 }}>
            Google ADK (Agent Development Kit) Architecture
          </div>
          <div style={{ fontSize: 11, color: '#8aaad0', lineHeight: 1.5 }}>
            <strong style={{ color: '#c5d8ff' }}>Agent:</strong> PandemicMCPAgent &nbsp;·&nbsp;
            <strong style={{ color: '#c5d8ff' }}>Protocol:</strong> MCP (Model Context Protocol) &nbsp;·&nbsp;
            <strong style={{ color: '#c5d8ff' }}>Tool:</strong> simulate_pandemic &nbsp;·&nbsp;
            <strong style={{ color: '#c5d8ff' }}>Data source:</strong> SEIR Epidemic Simulation Engine
          </div>
        </div>
      </div>

      {/* Agent Flow Visualization */}
      <div className="chart-card" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Agent Execution Flow
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center', gap: 4, flexWrap: 'wrap' }}>
          <FlowStep number="1" label="Receive Query" active={step >= 1} done={step > 1} />
          <ChevronRight size={14} color="var(--color-border-strong)" style={{ marginTop: 10 }} />
          <FlowStep number="2" label="Parse Intent (Region + Intervention)" active={step >= 2} done={step > 2} />
          <ChevronRight size={14} color="var(--color-border-strong)" style={{ marginTop: 10 }} />
          <FlowStep number="3" label="Call MCP Tool (simulate_pandemic)" active={step >= 3} done={step > 3} />
          <ChevronRight size={14} color="var(--color-border-strong)" style={{ marginTop: 10 }} />
          <FlowStep number="4" label="Get Structured Data" active={step >= 4} done={step > 4} />
          <ChevronRight size={14} color="var(--color-border-strong)" style={{ marginTop: 10 }} />
          <FlowStep number="5" label="Generate Response" active={step >= 4} done={step >= 4} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Input Panel */}
        <div className="chart-card">
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <MessageSquare size={14} color="var(--color-accent)" />
            Ask the MCP Agent
          </div>

          <textarea
            id="mcp-query-input"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), run())}
            placeholder="e.g. What is the impact of a lockdown in Delhi?"
            rows={3}
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'var(--color-surface-2)',
              border: '1px solid var(--color-border)',
              borderRadius: 8, padding: '10px 12px',
              color: 'var(--color-text-primary)',
              fontSize: 13, lineHeight: 1.5, resize: 'vertical',
              outline: 'none', fontFamily: 'inherit',
            }}
          />

          <button
            id="mcp-run-btn"
            className="btn btn-primary"
            onClick={() => run()}
            disabled={loading || !query.trim()}
            style={{ marginTop: 10, width: '100%', justifyContent: 'center' }}
          >
            {loading
              ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Running MCP Agent...</>
              : <><Play size={14} /> Run MCP Agent</>
            }
          </button>

          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Example queries
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {EXAMPLE_QUERIES.map((q, i) => (
                <button
                  key={i}
                  onClick={() => useExample(q)}
                  disabled={loading}
                  style={{
                    background: 'none', border: '1px solid var(--color-border)',
                    borderRadius: 6, padding: '6px 10px', cursor: 'pointer',
                    textAlign: 'left', fontSize: 11, color: 'var(--color-text-secondary)',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => { e.target.style.background = 'var(--color-surface-2)'; e.target.style.borderColor = 'var(--color-accent)' }}
                  onMouseLeave={e => { e.target.style.background = 'none'; e.target.style.borderColor = 'var(--color-border)' }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Result Panel */}
        <div className="chart-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Bot size={14} color="var(--color-accent)" />
            Agent Response
          </div>

          {error && (
            <div style={{
              background: 'var(--color-critical-light)', border: '1px solid var(--color-critical)',
              borderRadius: 8, padding: '12px 14px', display: 'flex', gap: 8, alignItems: 'flex-start',
            }}>
              <AlertCircle size={14} color="var(--color-critical)" style={{ flexShrink: 0, marginTop: 1 }} />
              <div style={{ fontSize: 12, color: 'var(--color-critical)' }}>{error}</div>
            </div>
          )}

          {!result && !error && !loading && (
            <div style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              color: 'var(--color-text-muted)', textAlign: 'center', padding: 24,
            }}>
              <Bot size={40} style={{ opacity: 0.2, marginBottom: 12 }} />
              <div style={{ fontSize: 13, fontWeight: 600 }}>Waiting for query</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>The agent will display its response here</div>
            </div>
          )}

          {loading && (
            <div style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              color: 'var(--color-text-muted)', textAlign: 'center', padding: 24, gap: 12,
            }}>
              <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
              <div style={{ fontSize: 13 }}>
                {step === 1 && 'Parsing query intent...'}
                {step === 2 && 'Calling simulate_pandemic MCP tool...'}
                {step >= 3 && 'Generating natural language response...'}
              </div>
            </div>
          )}

          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Parsed intent */}
              {intent && (
                <div style={{
                  background: 'var(--color-surface-2)', borderRadius: 8, padding: '10px 12px',
                  display: 'flex', gap: 16,
                }}>
                  <div style={{ fontSize: 11 }}>
                    <span style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>Region: </span>
                    <span style={{ color: 'var(--color-text-primary)', fontWeight: 700, textTransform: 'capitalize' }}>
                      {intent.region?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: 11 }}>
                    <span style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>Intervention: </span>
                    <span style={{ color: 'var(--color-text-primary)', fontWeight: 700, textTransform: 'capitalize' }}>
                      {intent.intervention?.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              )}

              {/* Natural language response */}
              <div style={{
                background: 'linear-gradient(135deg, var(--color-accent-light), #f0f4ff)',
                border: '1px solid var(--color-accent)',
                borderRadius: 8, padding: '14px 16px',
              }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--color-accent)', marginBottom: 6 }}>
                  AI Response
                </div>
                <div style={{ fontSize: 13, color: 'var(--color-text-primary)', lineHeight: 1.7 }}>
                  {result.response}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Structured Data Panel */}
      {data && (
        <div className="chart-card" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={14} color="var(--color-accent)" />
            MCP Tool Output — Structured Data
            <span className="badge badge-info" style={{ marginLeft: 4 }}>simulate_pandemic</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 16 }}>
            Raw structured JSON returned by the MCP tool — the agent used this data to generate its response
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
            <DataCard label="Peak Infections" value={fmt(data.peak_infected)} color="var(--color-critical)" sub={`Day ${data.peak_day}`} />
            <DataCard label="Total Infected" value={fmt(data.total_infected)} color="var(--color-high)" sub={`${data.attack_rate_pct}% attack rate`} />
            <DataCard label="Total Deceased" value={fmt(data.total_deceased)} color="#8e44ad" />
            <DataCard label="Baseline Peak" value={fmt(data.baseline_peak_infected)} color="#636e72" sub="No-action scenario" />
            <DataCard label="Reduction" value={`${data.reduction_percent}%`} color="var(--color-low)" sub="vs. no-action" />
            <DataCard label="Lives Saved" value={fmt(data.lives_saved)} color="var(--color-low)" sub="vs. no-action" />
            <DataCard label="R0" value={data.r0?.toFixed(2)} color="var(--color-accent)" sub="Effective reproduction" />
            <DataCard label="Population" value={fmt(data.population)} color="var(--color-text-muted)" sub={data.country} />
          </div>
        </div>
      )}

      {/* MCP Tool Call Details */}
      {result && (
        <div className="chart-card">
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Zap size={14} color="#f39c12" />
            MCP Tool Call Details
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                Tool Call
              </div>
              <pre style={{
                background: 'var(--color-surface-2)', borderRadius: 6, padding: '12px 14px',
                fontSize: 11, color: '#a8daff', lineHeight: 1.6, overflow: 'auto',
                margin: 0, fontFamily: 'var(--font-mono)',
              }}>
                {JSON.stringify(result.mcp_tool_call, null, 2)}
              </pre>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                Parsed Intent
              </div>
              <pre style={{
                background: 'var(--color-surface-2)', borderRadius: 6, padding: '12px 14px',
                fontSize: 11, color: '#a8daff', lineHeight: 1.6, overflow: 'auto',
                margin: 0, fontFamily: 'var(--font-mono)',
              }}>
                {JSON.stringify({ agent: result.agent, ...result.intent }, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
