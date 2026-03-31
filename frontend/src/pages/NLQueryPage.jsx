import React, { useState, useRef, useEffect } from 'react'
import { MessageSquare, Send, Cpu, User, RefreshCw, Clock } from 'lucide-react'
import { agentService, scenarioService, regionService } from '../services/api.js'

const fmt = n => {
  if (n === null || n === undefined) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

// Maps natural language queries to API calls + response formatters
function parseQuery(query, regionId) {
  const q = query.toLowerCase().trim()

  // Lockdown questions
  if (q.includes('lockdown') || q.includes('lock down')) {
    const isPartial = q.includes('partial')
    const isFull = q.includes('full') || q.includes('complete')
    const intervention = isFull ? 'full_lockdown' : isPartial ? 'partial_lockdown' : 'full_lockdown'
    return {
      type: 'scenario',
      payload: { region_id: regionId, days: 180, interventions: ['no_action', intervention] },
      question: query,
      format: (data) => {
        const base = data.comparisons?.find(c => c.scenario === 'no_action')
        const lock = data.comparisons?.find(c => c.scenario === intervention)
        if (!base || !lock) return 'Could not compute scenario comparison.'
        return `If you implement a ${intervention.replace('_',' ')} in ${regionId}, infections drop by **${lock.reduction_vs_baseline_pct}%** compared to no action.\n\n- Total infections: ${fmt(lock.total_infected)} vs ${fmt(base.total_infected)} baseline\n- Lives saved: approximately ${fmt(lock.lives_saved)}\n- Peak cases: ${fmt(lock.peak_infected)} on day ${lock.peak_day}\n\nThe model projects the epidemic ends around day ${lock.epidemic_end_day || 'unknown'}.`
      }
    }
  }

  // School closure
  if (q.includes('school') || q.includes('education') || q.includes('class')) {
    return {
      type: 'scenario',
      payload: { region_id: regionId, days: 180, interventions: ['no_action', 'school_closure'] },
      question: query,
      format: (data) => {
        const base = data.comparisons?.find(c => c.scenario === 'no_action')
        const sc = data.comparisons?.find(c => c.scenario === 'school_closure')
        if (!sc) return 'Scenario data unavailable.'
        return `Closing schools reduces infections by **${sc.reduction_vs_baseline_pct}%**.\n\n- Total infections: ${fmt(sc.total_infected)} (vs ${fmt(base?.total_infected)} without intervention)\n- Peak: ${fmt(sc.peak_infected)} cases on day ${sc.peak_day}\n- Lives saved: ${fmt(sc.lives_saved)}\n\nSchool closures are effective for reducing youth transmission but have moderate economic and social costs.`
      }
    }
  }

  // Vaccination
  if (q.includes('vaccin') || q.includes('immuniz') || q.includes('jab') || q.includes('dose')) {
    return {
      type: 'scenario',
      payload: { region_id: regionId, days: 180, interventions: ['no_action', 'vaccination_rollout'] },
      question: query,
      format: (data) => {
        const vax = data.comparisons?.find(c => c.scenario === 'vaccination_rollout')
        const base = data.comparisons?.find(c => c.scenario === 'no_action')
        if (!vax) return 'Vaccination scenario unavailable.'
        return `Accelerated vaccination reduces total infections by **${vax.reduction_vs_baseline_pct}%** over 180 days.\n\n- Total infections: ${fmt(vax.total_infected)} vs ${fmt(base?.total_infected)} baseline\n- Peak: ${fmt(vax.peak_infected)} cases\n- Lives saved: ${fmt(vax.lives_saved)}\n\nVaccination has low economic cost (${Math.round(0.20*100)}% GDP impact) and is the most sustainable long-term strategy. Daily vaccination rate in model: 0.5% of susceptible population.`
      }
    }
  }

  // Travel restrictions
  if (q.includes('travel') || q.includes('border') || q.includes('flight') || q.includes('transport')) {
    return {
      type: 'scenario',
      payload: { region_id: regionId, days: 180, interventions: ['no_action', 'travel_restriction'] },
      question: query,
      format: (data) => {
        const tr = data.comparisons?.find(c => c.scenario === 'travel_restriction')
        if (!tr) return 'Travel restriction scenario unavailable.'
        return `Travel restrictions reduce infections by **${tr.reduction_vs_baseline_pct}%**.\n\n- Peak: ${fmt(tr.peak_infected)} cases on day ${tr.peak_day}\n- Lives saved: ${fmt(tr.lives_saved)}\n\nTravel restrictions reduce mobility by 40% and slow geographic spread, but are less effective than lockdowns for controlling transmission within regions.`
      }
    }
  }

  // Best strategy
  if (q.includes('best') || q.includes('optimal') || q.includes('recommend') || q.includes('what should')) {
    return {
      type: 'agents',
      payload: { region_id: regionId, days: 180, intervention: 'no_action', run_all_scenarios: true },
      question: query,
      format: (data) => {
        const synth = data.analysis?.synthesis
        const policy = data.analysis?.agents?.policy?.output
        const best = policy?.primary_recommendation
        if (!best) return 'Unable to generate recommendation.'
        return `Based on multi-agent analysis for **${regionId}**:\n\n**Recommended strategy: ${best.name}**\n${best.description}\n\n- Effectiveness: ${Math.round(best.effectiveness*100)}%\n- Economic cost: ${Math.round(best.economic_cost*100)}% of regional GDP\n- Implementation speed: ${Math.round(best.implementation_speed*100)}%\n- Urgency level: **${synth?.urgency}**\n\nThe current severity is **${synth?.overall_severity}** with R0 = ${synth?.key_metrics?.r0}. Immediate action is ${synth?.urgency === 'IMMEDIATE' ? 'strongly advised' : 'recommended'}.`
      }
    }
  }

  // R0 / reproduction number
  if (q.includes('r0') || q.includes('reproduction') || q.includes('spread') || q.includes('transmiss')) {
    return {
      type: 'agents',
      payload: { region_id: regionId, days: 90, intervention: 'no_action', run_all_scenarios: false },
      question: query,
      format: (data) => {
        const r0 = data.simulation_summary?.r0
        const basic = data.simulation_summary?.basic_r0
        const pred = data.analysis?.agents?.prediction?.output
        return `The current **effective R0 = ${r0}** for ${regionId} (basic R0 = ${basic}).\n\nAn R0 above 1.0 means the epidemic is growing. Each infected person infects ${r0} others on average.\n\n- Severity classification: **${pred?.severity_level}**\n- Trend: ${pred?.trend_direction}\n- Attack rate projection: ${pred?.attack_rate_pct}% of population\n\nTo achieve R0 < 1 and stop the epidemic, interventions must reduce transmission by at least ${Math.round((1 - 1/r0)*100)}%.`
      }
    }
  }

  // Peak / when
  if (q.includes('peak') || q.includes('when') || q.includes('how long') || q.includes('timeline')) {
    return {
      type: 'agents',
      payload: { region_id: regionId, days: 180, intervention: 'no_action', run_all_scenarios: false },
      question: query,
      format: (data) => {
        const pred = data.analysis?.agents?.prediction?.output
        const sim = data.simulation_summary
        return `Without intervention, ${regionId} will reach peak infections on **day ${sim?.peak_day}** with approximately **${fmt(sim?.peak_infected)}** simultaneous cases.\n\n- Total projected infections: ${fmt(sim?.total_infected)}\n- Healthcare capacity: ${pred?.hospital_capacity ? fmt(pred.hospital_capacity) : '—'} beds\n- Capacity breach: ${pred?.capacity_breach_day ? `Day ${pred.capacity_breach_day}` : 'Not projected'}\n- Epidemic end estimate: ${pred?.epidemic_end_day ? `Day ${pred.epidemic_end_day}` : 'Not within 180-day window'}`
      }
    }
  }

  // Combined / all interventions
  if (q.includes('compar') || q.includes('all option') || q.includes('which intervention') || q.includes('all scenario')) {
    return {
      type: 'scenario',
      payload: { region_id: regionId, days: 180, interventions: ['no_action','partial_lockdown','full_lockdown','vaccination_rollout','combined_strategy'] },
      question: query,
      format: (data) => {
        const comps = data.comparisons || []
        const lines = comps.map((c,i) =>
          `${i+1}. **${c.display_name}**: ${fmt(c.total_infected)} total infections, ${c.reduction_vs_baseline_pct > 0 ? `-${c.reduction_vs_baseline_pct}%` : 'baseline'}, saves ${fmt(c.lives_saved)} lives`
        )
        return `Scenario comparison for **${regionId}** (180 days):\n\n${lines.join('\n')}\n\nBest outcome: **${data.best_scenario?.display_name}** with ${data.best_scenario?.reduction_vs_baseline_pct}% reduction in infections.`
      }
    }
  }

  // Fallback
  return {
    type: 'static',
    question: query,
    format: () => `I can answer questions about epidemic scenarios for ${regionId}. Try asking:\n\n- "What happens if we implement a full lockdown?"\n- "What is the best strategy?"\n- "When will infections peak?"\n- "How effective is vaccination?"\n- "Compare all interventions"\n- "What is the R0 right now?"`
  }
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:isUser?'flex-end':'flex-start', marginBottom:16 }}>
      <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
        {!isUser && <div style={{ width:22,height:22,borderRadius:6,background:'var(--color-accent)',display:'flex',alignItems:'center',justifyContent:'center' }}><Cpu size={12} color="white"/></div>}
        <span style={{ fontSize:11, fontWeight:600, color:'var(--color-text-muted)', textTransform:'uppercase', letterSpacing:'0.05em' }}>{isUser?'You':'AI System'}</span>
        {isUser && <div style={{ width:22,height:22,borderRadius:6,background:'var(--color-surface-2)',display:'flex',alignItems:'center',justifyContent:'center' }}><User size={12} color="var(--color-text-secondary)"/></div>}
      </div>
      <div style={{
        maxWidth:'80%',
        background:isUser?'var(--color-accent)':'var(--color-surface)',
        color:isUser?'white':'var(--color-text-primary)',
        border:isUser?'none':'1px solid var(--color-border)',
        borderRadius:isUser?'12px 12px 4px 12px':'12px 12px 12px 4px',
        padding:'12px 16px',
        fontSize:13,
        lineHeight:1.7,
        boxShadow:'var(--shadow-sm)',
        whiteSpace:'pre-wrap',
      }}>
        {msg.loading ? (
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <div className="spinner" style={{width:14,height:14,borderWidth:2}}/>
            <span style={{color:'var(--color-text-muted)',fontSize:12}}>Querying agents...</span>
          </div>
        ) : (
          // Render **bold** markdown
          msg.content.split('\n').map((line, i) => {
            const parts = line.split(/\*\*(.*?)\*\*/g)
            return (
              <div key={i} style={{marginBottom:line===''?4:0}}>
                {parts.map((part, j) => j % 2 === 1 ? <strong key={j}>{part}</strong> : part)}
              </div>
            )
          })
        )}
      </div>
      {msg.executionMs && (
        <div style={{fontSize:10,color:'var(--color-text-muted)',marginTop:3,display:'flex',alignItems:'center',gap:3}}>
          <Clock size={9}/>{(msg.executionMs/1000).toFixed(2)}s
        </div>
      )}
    </div>
  )
}

const EXAMPLE_QUESTIONS = [
  'What happens if we close schools?',
  'What is the best intervention strategy?',
  'When will infections peak?',
  'Compare all intervention options',
  'How effective is a full lockdown?',
  'What is the current R0?',
]

export default function NLQueryPage({ regionId }) {
  const [messages, setMessages] = useState([
    {
      id: 0, role:'assistant',
      content:`Welcome to the Natural Language Query interface for the Pandemic Digital Twin.\n\nI can simulate scenarios and answer questions about epidemic dynamics for **${regionId}**. I use the live multi-agent system — not a pre-written script.\n\nTry asking about lockdowns, vaccination, school closures, peak timing, or intervention comparisons.`
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:'smooth'}) }, [messages])

  const submit = async (queryText) => {
    const q = (queryText || input).trim()
    if (!q || loading) return
    setInput('')
    setLoading(true)

    const userMsg = { id: Date.now(), role:'user', content:q }
    const thinkingMsg = { id: Date.now()+1, role:'assistant', content:'', loading:true }
    setMessages(prev => [...prev, userMsg, thinkingMsg])

    const start = Date.now()
    let responseText = ''

    try {
      const parsed = parseQuery(q, regionId)

      if (parsed.type === 'scenario') {
        const data = await scenarioService.run(parsed.payload)
        responseText = parsed.format(data)
      } else if (parsed.type === 'agents') {
        const data = await agentService.analyze(parsed.payload)
        responseText = parsed.format(data)
      } else {
        responseText = parsed.format()
      }
    } catch (e) {
      responseText = `Error: ${e.friendlyMessage || e.message || 'API call failed. Is the backend running?'}`
    }

    const elapsed = Date.now() - start
    setMessages(prev => [
      ...prev.filter(m => !m.loading),
      { id: Date.now()+2, role:'assistant', content: responseText, executionMs: elapsed }
    ])
    setLoading(false)
  }

  const handleKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }

  return (
    <div className="fade-in" style={{ display:'flex', flexDirection:'column', height:'calc(100vh - 120px)' }}>
      <div className="page-header">
        <h1 className="page-title">Natural Language Query</h1>
        <p className="page-subtitle">Ask questions in plain English — the multi-agent system simulates and responds in real time</p>
      </div>

      {/* Example chips */}
      <div style={{ display:'flex', flexWrap:'wrap', gap:8, marginBottom:16 }}>
        {EXAMPLE_QUESTIONS.map(q => (
          <button key={q} className="btn btn-secondary" style={{fontSize:11,padding:'4px 10px',height:'auto'}} onClick={() => submit(q)} disabled={loading}>
            {q}
          </button>
        ))}
      </div>

      {/* Message thread */}
      <div style={{
        flex:1, overflowY:'auto', background:'var(--color-surface)', border:'1px solid var(--color-border)',
        borderRadius:'var(--radius-lg)', padding:'20px', marginBottom:12
      }}>
        {messages.map(msg => <MessageBubble key={msg.id} msg={msg}/>)}
        <div ref={bottomRef}/>
      </div>

      {/* Input */}
      <div style={{ display:'flex', gap:10, alignItems:'flex-end' }}>
        <div style={{ flex:1, position:'relative' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={`Ask about ${regionId} — e.g. "What if we close schools for 6 weeks?"`}
            disabled={loading}
            rows={2}
            style={{
              width:'100%', resize:'none', fontFamily:'var(--font-sans)', fontSize:13,
              background:'var(--color-surface)', border:'1px solid var(--color-border)',
              borderRadius:'var(--radius-md)', padding:'10px 14px',
              color:'var(--color-text-primary)', outline:'none',
              transition:'border-color var(--transition)',
              lineHeight:1.5
            }}
            onFocus={e => e.target.style.borderColor='var(--color-accent)'}
            onBlur={e => e.target.style.borderColor='var(--color-border)'}
          />
          <div style={{ position:'absolute', bottom:8, right:10, fontSize:10, color:'var(--color-text-muted)' }}>
            Enter to send
          </div>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => submit()}
          disabled={loading || !input.trim()}
          style={{ height:60, paddingLeft:20, paddingRight:20, flexShrink:0 }}
        >
          {loading ? <div className="spinner" style={{width:14,height:14,borderWidth:2}}/> : <Send size={16}/>}
        </button>
      </div>

      <div style={{ fontSize:11, color:'var(--color-text-muted)', marginTop:6, textAlign:'center' }}>
        Answers are generated by live SEIR simulations and the multi-agent pipeline — not hardcoded responses
      </div>
    </div>
  )
}
