import React, { useState, useEffect, useCallback } from 'react'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts'
import {
  AlertTriangle, TrendingUp, Users, Activity,
  Thermometer, RefreshCw, ArrowUp, ArrowDown,
  Shield, Target, Clock, Zap
} from 'lucide-react'
import { regionService, agentService } from '../services/api.js'
import RegionMap from '../components/Map/RegionMap.jsx'

const fmt = n => {
  if (n === null || n === undefined) return '—'
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return Math.round(n).toLocaleString()
}

const SeverityBadge = ({ level }) => {
  const cls = { CRITICAL:'badge-critical', HIGH:'badge-high', MODERATE:'badge-moderate', LOW:'badge-low' }[level] || 'badge-info'
  return <span className={`badge ${cls}`}>{level || '—'}</span>
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background:'white', border:'1px solid var(--color-border)', borderRadius:8, padding:'10px 14px', boxShadow:'var(--shadow-md)', fontSize:12 }}>
      <div style={{ fontWeight:600, marginBottom:6, color:'var(--color-text-primary)' }}>Day {label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color:p.color, display:'flex', gap:8, justifyContent:'space-between', marginBottom:2 }}>
          <span>{p.name}</span>
          <span style={{ fontFamily:'var(--font-mono)', fontWeight:600 }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

const StatCard = ({ label, value, delta, deltaDir, sub, accent }) => (
  <div className="stat-card" style={accent ? { borderTop:`3px solid ${accent}` } : {}}>
    <div className="stat-label">{label}</div>
    <div className="stat-value">{value}</div>
    {delta && <div className={`stat-delta ${deltaDir || ''}`}>{deltaDir==='up'?<ArrowUp size={11}/>:<ArrowDown size={11}/>} {delta}</div>}
    {sub && <div className="stat-delta">{sub}</div>}
  </div>
)

export default function Dashboard({ regionId }) {
  const [data, setData] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [regionData, agentData] = await Promise.all([
        regionService.getById(regionId),
        agentService.analyze({ region_id: regionId, days: 180, intervention: 'no_action', run_all_scenarios: true })
      ])
      setData(regionData); setAnalysis(agentData); setLastUpdated(new Date())
    } catch (e) {
      setError(e.friendlyMessage || 'Failed to load. Ensure the backend is running on port 8000.')
    } finally { setLoading(false) }
  }, [regionId])

  useEffect(() => { load() }, [load])

  if (loading) return (
    <div className="loading-container">
      <div className="spinner" />
      <div className="loading-text">Simulating {regionId} — running 5 scenario models...</div>
    </div>
  )
  if (error) return (
    <div>
      <div className="error-banner">{error}</div>
      <button className="btn btn-primary" onClick={load}><RefreshCw size={14}/> Retry</button>
    </div>
  )

  const region = data?.region
  const stats = data?.disease_stats
  const weather = data?.weather
  const historical = data?.historical_data || []
  const synthesis = analysis?.analysis?.synthesis || {}
  const agents = analysis?.analysis?.agents || {}
  const predOut = agents.prediction?.output || {}
  const riskOut = agents.risk?.output || {}
  const policyOut = agents.policy?.output || {}
  const simOut = agents.simulation?.output || {}

  const chartData = historical.slice(-60).map((d,i)=>({
    day: i+1, date:d.date, active:d.active_cases, new:d.new_cases,
    recovered:d.new_recovered, deaths:d.new_deaths
  }))

  const severity = synthesis.overall_severity || 'MODERATE'
  const urgency = synthesis.urgency || 'STANDARD'

  // Radar chart data for risk factors
  const radarData = riskOut.zones?.slice(0,1).map(z=>([
    { factor:'Density',     value: Math.min(100,(z.population_density/500)) },
    { factor:'Mobility',    value: (z.mobility_index||0.7)*100 },
    { factor:'Cases',       value: Math.min(100,(z.current_cases/(z.population||1))*5000) },
    { factor:'Capacity',    value: 100-Math.min(100,(z.hospital_beds_per_1000||3)*10) },
    { factor:'Elderly',     value: (z.elderly_population_pct||15)*3 },
  ]))[0] || []

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between' }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:4 }}>
            <h1 className="page-title">{region?.name}</h1>
            <SeverityBadge level={severity}/>
            <span className={`badge badge-${urgency==='IMMEDIATE'?'critical':urgency==='URGENT'?'high':'moderate'}`}>{urgency}</span>
          </div>
          <p className="page-subtitle">
            {region?.country} — Population {fmt(region?.population)} — Updated {lastUpdated?.toLocaleTimeString()}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={load} disabled={loading}><RefreshCw size={14}/> Refresh</button>
      </div>

      {/* Alert banners */}
      {riskOut.alerts?.slice(0,2).map((alert,i)=>(
        <div key={i} className={`alert-banner alert-${alert.level?.toLowerCase()}`}>
          <AlertTriangle size={15} style={{flexShrink:0,marginTop:1}}/>
          <span><strong>{alert.zone}:</strong> {alert.message}</span>
        </div>
      ))}

      {/* KPI row 1 */}
      <div className="grid-4" style={{marginBottom:16}}>
        <StatCard label="Active Cases" value={fmt(stats?.active_cases)} delta={`${stats?.positivity_rate}% positivity`} deltaDir="up" accent="var(--color-critical)"/>
        <StatCard label="Effective R0" value={predOut.r0 || stats?.reproduction_number?.toFixed(2)} sub={`Basic R0 = ${analysis?.simulation_summary?.basic_r0 || '—'}`} accent={predOut.r0>2?'var(--color-critical)':predOut.r0>1?'var(--color-high)':'var(--color-low)'}/>
        <StatCard label="Vaccination Coverage" value={`${stats?.vaccination_coverage||0}%`} sub={`${fmt(region?.population*(stats?.vaccination_coverage/100))} vaccinated`} accent="var(--color-low)"/>
        <StatCard label="Hospitalized" value={fmt(stats?.hospitalized)} sub={`ICU: ${fmt(stats?.icu)}`} accent="var(--color-accent)"/>
      </div>

      {/* KPI row 2 */}
      <div className="grid-4" style={{marginBottom:20}}>
        <StatCard label="Projected Peak" value={fmt(predOut.peak_infected)} sub={`Day ${predOut.peak_day||'—'}`}/>
        <StatCard label="Attack Rate" value={`${predOut.attack_rate_pct||'—'}%`} sub="of population"/>
        <StatCard label="High Risk Zones" value={riskOut.high_risk_count||'—'} sub={`of ${riskOut.total_zones_analyzed||'—'} zones`}/>
        <StatCard label="Total Deaths" value={fmt(stats?.total_deaths)} sub={`${fmt(stats?.total_recovered)} recovered`}/>
      </div>

      {/* Main charts row */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,marginBottom:16}}>
        <div className="chart-card">
          <div className="chart-card-header">
            <div><div className="chart-card-title">60-Day Epidemic Trend</div><div className="chart-card-sub">Active cases, new cases, recoveries</div></div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{top:5,right:10,left:0,bottom:0}}>
              <defs>
                <linearGradient id="ag1" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#e74c3c" stopOpacity={0.15}/><stop offset="95%" stopColor="#e74c3c" stopOpacity={0}/></linearGradient>
                <linearGradient id="ag2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#1a56db" stopOpacity={0.12}/><stop offset="95%" stopColor="#1a56db" stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)"/>
              <XAxis dataKey="day" tick={{fontSize:11,fill:'var(--color-text-muted)'}}/>
              <YAxis tick={{fontSize:11,fill:'var(--color-text-muted)'}} tickFormatter={fmt}/>
              <Tooltip content={<CustomTooltip/>}/>
              <Legend wrapperStyle={{fontSize:12}}/>
              <Area type="monotone" dataKey="active" name="Active" stroke="#e74c3c" fill="url(#ag1)" strokeWidth={2}/>
              <Area type="monotone" dataKey="new" name="New Cases" stroke="#1a56db" fill="url(#ag2)" strokeWidth={1.5}/>
              <Line type="monotone" dataKey="recovered" name="Recovered" stroke="#27ae60" strokeWidth={1.5} dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card" style={{padding:0,overflow:'hidden',borderRadius:'var(--radius-lg)'}}>
          <div style={{padding:'16px 20px 12px',borderBottom:'1px solid var(--color-border)'}}>
            <div className="chart-card-title">Zone Risk Map</div>
            <div className="chart-card-sub">{region?.name} — colour-coded by composite risk score</div>
          </div>
          <RegionMap region={region} zones={riskOut.zones||region?.zones||[]} height={220}/>
        </div>
      </div>

      {/* Scenario comparison summary + risk radar */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,marginBottom:16}}>
        {/* Best scenario from simulation agent */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div><div className="chart-card-title">Scenario Outcomes</div><div className="chart-card-sub">What-if comparison from simulation agent</div></div>
          </div>
          {simOut.scenario_comparisons?.length > 0 ? (
            <div style={{display:'flex',flexDirection:'column',gap:6}}>
              {simOut.scenario_comparisons.slice(0,5).map((s,i)=>(
                <div key={s.scenario} style={{display:'flex',alignItems:'center',gap:10,padding:'7px 0',borderBottom:i<4?'1px solid var(--color-border)':'none'}}>
                  <span style={{width:20,height:20,borderRadius:4,background:i===0?'var(--color-low-light)':'var(--color-surface-2)',color:i===0?'var(--color-low)':'var(--color-text-muted)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:700,flexShrink:0}}>{i+1}</span>
                  <span style={{fontSize:12,fontWeight:600,flex:1,color:'var(--color-text-primary)'}}>{s.scenario.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</span>
                  <div style={{display:'flex',alignItems:'center',gap:6}}>
                    <div style={{width:60,height:5,background:'var(--color-surface-2)',borderRadius:2,overflow:'hidden'}}>
                      <div style={{width:`${Math.max(0,s.reduction_vs_baseline)}%`,height:'100%',background:i===0?'var(--color-low)':'var(--color-accent)',borderRadius:2}}/>
                    </div>
                    <span style={{fontSize:11,fontFamily:'var(--font-mono)',fontWeight:600,color:s.reduction_vs_baseline>0?'var(--color-low)':'var(--color-text-muted)',width:36,textAlign:'right'}}>{s.reduction_vs_baseline>0?`-${s.reduction_vs_baseline}%`:'Base'}</span>
                  </div>
                </div>
              ))}
              {simOut.best_scenario && (
                <div style={{marginTop:8,padding:'8px 10px',background:'var(--color-low-light)',borderRadius:6,fontSize:11,color:'var(--color-low)'}}>
                  Best: <strong>{simOut.best_scenario.scenario?.replace(/_/g,' ')}</strong> — saves {fmt(simOut.best_scenario.lives_saved)} lives
                </div>
              )}
            </div>
          ) : (
            <div style={{fontSize:13,color:'var(--color-text-muted)',textAlign:'center',padding:'20px 0'}}>Run scenario analysis to see comparisons</div>
          )}
        </div>

        {/* Risk radar chart */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div><div className="chart-card-title">Risk Factor Radar</div><div className="chart-card-sub">Top zone composite risk breakdown</div></div>
          </div>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData} margin={{top:0,right:20,left:20,bottom:0}}>
                <PolarGrid stroke="var(--color-border)"/>
                <PolarAngleAxis dataKey="factor" tick={{fontSize:11,fill:'var(--color-text-secondary)'}}/>
                <PolarRadiusAxis angle={90} domain={[0,100]} tick={{fontSize:9,fill:'var(--color-text-muted)'}}/>
                <Radar name="Risk" dataKey="value" stroke="var(--color-critical)" fill="var(--color-critical)" fillOpacity={0.12} strokeWidth={2}/>
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{fontSize:13,color:'var(--color-text-muted)',textAlign:'center',padding:'30px 0'}}>No zone data available</div>
          )}
        </div>
      </div>

      {/* Policy recommendation + zone rankings */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,marginBottom:16}}>
        <div className="chart-card">
          <div className="chart-card-header">
            <div><div className="chart-card-title">AI Policy Recommendation</div><div className="chart-card-sub">Multi-agent consensus</div></div>
            {policyOut.urgency_level && <span className={`badge badge-${policyOut.urgency_level==='IMMEDIATE'?'critical':policyOut.urgency_level==='URGENT'?'high':'moderate'}`}>{policyOut.urgency_level}</span>}
          </div>
          {policyOut.primary_recommendation && (
            <div style={{background:'var(--color-accent-light)',border:'1px solid #c7d8f8',borderRadius:'var(--radius-md)',padding:'14px 16px',marginBottom:14}}>
              <div style={{fontSize:15,fontWeight:700,color:'var(--color-accent)',marginBottom:4}}>{policyOut.primary_recommendation.name}</div>
              <div style={{fontSize:12,color:'var(--color-text-secondary)',lineHeight:1.5,marginBottom:10}}>{policyOut.primary_recommendation.description}</div>
              <div style={{display:'flex',gap:16}}>
                <span style={{fontSize:11,color:'var(--color-text-muted)'}}>Effectiveness <strong style={{color:'var(--color-low)'}}>{Math.round((policyOut.primary_recommendation.effectiveness||0)*100)}%</strong></span>
                <span style={{fontSize:11,color:'var(--color-text-muted)'}}>Econ Cost <strong style={{color:'var(--color-high)'}}>{Math.round((policyOut.primary_recommendation.economic_cost||0)*100)}%</strong></span>
                <span style={{fontSize:11,color:'var(--color-text-muted)'}}>Duration <strong>{policyOut.primary_recommendation.duration_weeks}w</strong></span>
              </div>
            </div>
          )}
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            {synthesis.top_recommendations?.slice(0,4).map((rec,i)=>(
              <div key={i} style={{display:'flex',gap:8,alignItems:'flex-start',fontSize:12,color:'var(--color-text-secondary)',lineHeight:1.5}}>
                <span style={{minWidth:18,height:18,background:'var(--color-accent)',color:'white',borderRadius:4,display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:700,flexShrink:0,marginTop:1}}>{i+1}</span>
                <span>{rec}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-card-header"><div><div className="chart-card-title">Zone Risk Rankings</div><div className="chart-card-sub">Sorted by composite risk score (0-100)</div></div></div>
          <div style={{display:'flex',flexDirection:'column',gap:2}}>
            {(riskOut.zones||[]).slice(0,6).map((zone,i)=>(
              <div key={zone.id} style={{display:'flex',alignItems:'center',gap:10,padding:'7px 0',borderBottom:i<5?'1px solid var(--color-border)':'none'}}>
                <span style={{width:22,height:22,background:i<2?'var(--color-critical-light)':'var(--color-surface-2)',color:i<2?'var(--color-critical)':'var(--color-text-muted)',borderRadius:4,display:'flex',alignItems:'center',justifyContent:'center',fontSize:11,fontWeight:700,flexShrink:0}}>{i+1}</span>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontSize:12,fontWeight:600,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{zone.name}</div>
                  <div style={{fontSize:11,color:'var(--color-text-muted)'}}>{fmt(zone.population)} pop</div>
                </div>
                <div style={{display:'flex',alignItems:'center',gap:6}}>
                  <div style={{width:50,height:4,background:'var(--color-surface-2)',borderRadius:2,overflow:'hidden'}}>
                    <div style={{width:`${zone.risk_score}%`,height:'100%',borderRadius:2,background:zone.risk_level==='CRITICAL'?'var(--color-critical)':zone.risk_level==='HIGH'?'var(--color-high)':zone.risk_level==='MODERATE'?'var(--color-moderate)':'var(--color-low)'}}/>
                  </div>
                  <span style={{fontSize:11,fontFamily:'var(--font-mono)',fontWeight:600,width:28,textAlign:'right'}}>{zone.risk_score}</span>
                  <SeverityBadge level={zone.risk_level}/>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent confidence panel + weather */}
      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:16}}>
        <div className="chart-card">
          <div className="chart-card-header"><div className="chart-card-title">Agent Confidence Summary</div></div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:10}}>
            {[
              {label:'Prediction',key:'prediction',icon:TrendingUp,color:'var(--color-accent)'},
              {label:'Risk',key:'risk',icon:AlertTriangle,color:'var(--color-high)'},
              {label:'Policy',key:'policy',icon:Shield,color:'var(--color-moderate)'},
              {label:'Simulation',key:'simulation',icon:Activity,color:'var(--color-low)'},
            ].map(({label,key,icon:Icon,color})=>{
              const conf = synthesis.confidence_summary?.[key] || 0
              return (
                <div key={key} style={{textAlign:'center',padding:'12px 8px',background:'var(--color-surface-2)',borderRadius:8}}>
                  <Icon size={16} color={color} style={{margin:'0 auto 6px',display:'block'}}/>
                  <div style={{fontSize:20,fontWeight:700,fontFamily:'var(--font-mono)',color}}>{Math.round(conf*100)}%</div>
                  <div style={{fontSize:10,color:'var(--color-text-muted)',marginTop:2,textTransform:'uppercase',letterSpacing:'0.05em'}}>{label}</div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-card-header"><div className="chart-card-title" style={{display:'flex',alignItems:'center',gap:6}}><Thermometer size={14}/> Environment</div></div>
          <div style={{display:'flex',flexDirection:'column',gap:8}}>
            {weather && [
              {label:'Temperature',value:`${weather.temperature}°C (${weather.conditions})`},
              {label:'Humidity',value:`${weather.humidity}%`},
              {label:'Wind Speed',value:`${weather.wind_speed} km/h`},
              {label:'Air Quality',value:`AQI ${weather.air_quality_index}`},
            ].map(({label,value})=>(
              <div key={label} style={{display:'flex',justifyContent:'space-between',fontSize:12}}>
                <span style={{color:'var(--color-text-muted)'}}>{label}</span>
                <span style={{fontWeight:600,color:'var(--color-text-primary)'}}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
