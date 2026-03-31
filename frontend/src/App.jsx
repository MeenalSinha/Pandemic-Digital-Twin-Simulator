import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import {
  Activity, BarChart3, Cpu, FlaskConical,
  Globe, ChevronRight, Wifi, WifiOff, MessageSquare, Play, Bot
} from 'lucide-react'
import Dashboard from './pages/Dashboard.jsx'
import SimulationPage from './pages/SimulationPage.jsx'
import ScenarioPage from './pages/ScenarioPage.jsx'
import AgentsPage from './pages/AgentsPage.jsx'
import RegionsPage from './pages/RegionsPage.jsx'
import NLQueryPage from './pages/NLQueryPage.jsx'
import DemoPage from './pages/DemoPage.jsx'
import MCPAgentPage from './pages/MCPAgentPage.jsx'
import { regionService } from './services/api.js'
import './App.css'

const NAV_ITEMS = [
  { path: '/',           label: 'Dashboard',  icon: Activity,      exact: true },
  { path: '/demo',       label: 'Live Demo',  icon: Play,          highlight: true },
  { path: '/mcp-agent',  label: 'MCP Agent',  icon: Bot,           highlight2: true },
  { path: '/simulation', label: 'Simulation', icon: FlaskConical },
  { path: '/scenarios',  label: 'Scenarios',  icon: BarChart3 },
  { path: '/agents',     label: 'AI Agents',  icon: Cpu },
  { path: '/query',      label: 'NL Query',   icon: MessageSquare },
  { path: '/regions',    label: 'Regions',    icon: Globe },
]

const DEFAULT_REGIONS = [
  { id: 'delhi',     name: 'Delhi NCR',          country: 'India'  },
  { id: 'mumbai',    name: 'Mumbai Metropolitan', country: 'India'  },
  { id: 'new_york',  name: 'New York City',       country: 'USA'    },
  { id: 'london',    name: 'Greater London',      country: 'UK'     },
  { id: 'tokyo',     name: 'Tokyo Metropolis',    country: 'Japan'  },
  { id: 'sao_paulo', name: 'Sao Paulo',           country: 'Brazil' },
]

function Sidebar({ apiOnline }) {
  const location = useLocation()
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon"><Activity size={18} strokeWidth={2.5}/></div>
        <div className="brand-text">
          <span className="brand-title">PandemicTwin</span>
          <span className="brand-sub">Digital Simulator v3</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        <span className="nav-section-label">Navigation</span>
        {NAV_ITEMS.map(({ path, label, icon: Icon, exact, highlight, highlight2 }) => (
          <NavLink key={path} to={path} end={exact}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            style={highlight ? ({ isActive }) => ({
              background: isActive ? 'var(--color-accent-light)' : 'var(--color-accent)',
              color: isActive ? 'var(--color-accent)' : 'white',
              fontWeight: 700, marginBottom: 6, marginTop: 2,
            }) : highlight2 ? ({ isActive }) => ({
              background: isActive ? '#1a3a2a' : '#14532d',
              color: isActive ? '#4ade80' : '#86efac',
              fontWeight: 700, marginBottom: 6,
            }) : undefined}
          >
            <Icon size={16} strokeWidth={1.75}/>
            <span>{label}</span>
            {location.pathname === path && <ChevronRight size={14} className="nav-active-indicator"/>}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className={`api-status ${apiOnline ? 'online' : 'offline'}`}>
          {apiOnline ? <Wifi size={13}/> : <WifiOff size={13}/>}
          <span>API {apiOnline ? 'Connected' : 'Disconnected'}</span>
        </div>
        <div className="version-badge">v3.0.0</div>
      </div>
    </aside>
  )
}

function TopBar({ selectedRegion, onRegionChange, regions }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <span className="topbar-label">Active Region</span>
        <select value={selectedRegion} onChange={e => onRegionChange(e.target.value)} className="region-selector">
          {regions.map(r => <option key={r.id} value={r.id}>{r.name} — {r.country}</option>)}
        </select>
      </div>
      <div className="topbar-right">
        <div className="live-indicator"><span className="live-dot"/><span>Live Simulation</span></div>
        <span className="topbar-time">
          {new Date().toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' })}
        </span>
      </div>
    </header>
  )
}

function AppLayout({ children, selectedRegion, onRegionChange, regions, apiOnline }) {
  return (
    <div className="app-layout">
      <Sidebar apiOnline={apiOnline}/>
      <div className="main-content">
        <TopBar selectedRegion={selectedRegion} onRegionChange={onRegionChange} regions={regions}/>
        <main className="page-content">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  const [selectedRegion, setSelectedRegion] = useState('delhi')
  const [regions, setRegions] = useState(DEFAULT_REGIONS)
  const [apiOnline, setApiOnline] = useState(false)

  useEffect(() => {
    fetch('/api/health')
      .then(r => { if (r.ok) { setApiOnline(true); return regionService.getAll() } throw new Error() })
      .then(d => { if (d?.regions?.length) setRegions(d.regions) })
      .catch(() => setApiOnline(false))
  }, [])

  return (
    <BrowserRouter>
      <AppLayout selectedRegion={selectedRegion} onRegionChange={setSelectedRegion}
        regions={regions} apiOnline={apiOnline}>
        <Routes>
          <Route path="/"           element={<Dashboard     regionId={selectedRegion}/>}/>
          <Route path="/demo"       element={<DemoPage      regionId={selectedRegion}/>}/>
          <Route path="/mcp-agent"  element={<MCPAgentPage  regionId={selectedRegion}/>}/>
          <Route path="/simulation" element={<SimulationPage regionId={selectedRegion}/>}/>
          <Route path="/scenarios"  element={<ScenarioPage  regionId={selectedRegion}/>}/>
          <Route path="/agents"     element={<AgentsPage    regionId={selectedRegion}/>}/>
          <Route path="/query"      element={<NLQueryPage   regionId={selectedRegion}/>}/>
          <Route path="/regions"    element={<RegionsPage/>}/>
        </Routes>
      </AppLayout>
    </BrowserRouter>
  )
}
