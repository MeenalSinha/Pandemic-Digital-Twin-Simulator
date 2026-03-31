# Pandemic Digital Twin Simulator

An AI-powered, end-to-end epidemic simulation platform that models disease spread in real time and recommends optimal public health interventions using a multi-agent architecture, MCP (Model Context Protocol), RAG knowledge retrieval, and live external data APIs.

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Folder Structure](#folder-structure)
5. [Setup Instructions](#setup-instructions)
6. [API Reference](#api-reference)
7. [Intervention Strategies](#intervention-strategies)
8. [Multi-Agent Pipeline](#multi-agent-pipeline)
9. [MCP Agent (PandemicMCPAgent)](#mcp-agent-pandemicmcpagent)
10. [RAG Knowledge Base](#rag-knowledge-base)
11. [Real-Time Data Sources](#real-time-data-sources)
12. [Economic Model](#economic-model)
13. [Adaptive Learning](#adaptive-learning)
14. [Supported Regions](#supported-regions)
15. [Tech Stack](#tech-stack)
16. [Demo Flow](#demo-flow)
17. [Deployment](#deployment)
18. [Extending to Production](#extending-to-production)

---

## Overview

The Pandemic Digital Twin Simulator creates a computational replica of a real-world region and models disease dynamics using a hybrid SEIR epidemiological model enhanced by a multi-agent AI orchestration system. It is designed for autonomous decision-making and scenario analysis, not conversational interaction.

The system integrates:

- **SEIR ODE solver** (scipy) for deterministic epidemic modeling
- **4-agent AI orchestration** for collaborative analysis and policy recommendation
- **PandemicMCPAgent** — an ADK-compatible agent using Model Context Protocol
- **FAISS-backed RAG knowledge base** for evidence-grounded responses
- **Live external APIs** (Open-Meteo weather, disease.sh COVID stats)
- **Economic cost-benefit model** with WHO cost-effectiveness thresholds
- **Adaptive learning service** that calibrates from simulation history
- **SQLite / PostgreSQL database** for persistence across sessions

---

## Key Features

| Feature | Description |
|---|---|
| SEIR Simulation | scipy ODE solver with intervention and environmental parameter adjustment |
| 4-Agent Pipeline | Prediction, Risk Analysis, Policy Recommendation, and Simulation agents |
| MCP Agent | ADK-compatible PandemicMCPAgent with `simulate_pandemic` MCP tool |
| RAG | FAISS + TF-IDF local vector search over 13 pandemic research documents |
| LLM Integration | Gemini 2.5 Pro for natural language interpretation (optional; analytical fallback included) |
| Real-Time Data | Live weather (Open-Meteo) and disease stats (disease.sh) — no API keys required |
| Economic Model | Dollar-cost analysis, ICU/bed requirements, DALYs, WHO cost-effectiveness thresholds |
| Adaptive Learning | Agents calibrate from historical simulation database |
| 7 Interventions | No action through combined targeted strategy |
| 6 Regions | Delhi, Mumbai, New York, London, Tokyo, Sao Paulo |
| Full-Stack UI | React 18 + Recharts + Leaflet dashboard with real-time charts and zone risk maps |

---

## Architecture

### System Data Flow

```
Real-World APIs (Open-Meteo, disease.sh)
         │
    RealTimeDataService (weather, disease stats, AQI, mobility)
         │
    DataIngestionService (regional parameters, zone breakdown)
         │
    SEIRModel (scipy ODE solver — beta, sigma, gamma, mu)
         │
    AgentOrchestrator (async pipeline)
    ├── PredictionAgent  ──────────────────┐
    ├── RiskAnalysisAgent  ────────────────┤──> Shared State ──> Synthesis
    ├── PolicyRecommendationAgent (+ RAG)  ┘
    └── SimulationAgent (what-if scenarios)
         │
    LLMService (Gemini 2.5 Pro / analytical fallback)
         │
    FastAPI REST + SQLite/PostgreSQL
         │
    React Dashboard (Recharts, Leaflet, real-time updates)
```

### MCP Agent Flow (PandemicMCPAgent)

```
Natural Language Query
         │
    IntentParser (region + intervention extraction)
         │
    MCPToolCall → simulate_pandemic (MCP Tool)
         │
    SEIR Engine → Structured JSON Data
         │
    LLM / Template → Natural Language Response
```

### Multi-Agent Communication

Agents run in an async shared-state pipeline:

1. **Prediction Agent** + **Risk Agent** run in parallel
2. **Policy Agent** receives both outputs for enriched analysis
3. **Simulation Agent** receives all three outputs for scenario comparison
4. **Orchestrator** synthesizes a unified recommendation with confidence summary

---

## Folder Structure

```
pandemic-digital-twin/
├── backend/
│   ├── main.py                    # FastAPI app entry point + lifespan init
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── agents/
│   │   ├── orchestrator.py        # 4-agent pipeline (Prediction/Risk/Policy/Simulation)
│   │   └── mcp_agent.py           # PandemicMCPAgent (ADK-compatible, MCP protocol)
│   ├── models/
│   │   └── seir_model.py          # SEIR ODE solver + intervention parameter application
│   ├── routes/
│   │   ├── simulate.py            # POST /api/simulate
│   │   ├── predict.py             # POST /api/predict
│   │   ├── recommend.py           # POST /api/recommend
│   │   ├── scenario.py            # POST /api/scenario
│   │   ├── regions.py             # GET  /api/regions
│   │   ├── agents.py              # POST /api/agents/analyze
│   │   ├── rag.py                 # POST /api/rag/query, /api/rag/nl-query
│   │   ├── realtime.py            # GET  /api/realtime/{region_id}
│   │   ├── economics.py           # POST /api/economics/analyze
│   │   ├── adaptive.py            # GET  /api/adaptive/insights/{region_id}
│   │   └── mcp_agent.py           # POST /mcp-agent
│   └── services/
│       ├── data_service.py        # Region data, SEIR parameters, zone generation
│       ├── realtime_service.py    # Live weather + disease APIs (TTL cache)
│       ├── llm_service.py         # Gemini 2.5 Pro + RAG context injection
│       ├── rag_service.py         # FAISS vector KB + TF-IDF embedder
│       ├── db_service.py          # SQLAlchemy async (SQLite / PostgreSQL)
│       ├── economic_model.py      # Dollar costs, DALYs, WHO thresholds
│       └── adaptive_service.py    # Parameter adaptation from simulation history
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── src/
│       ├── App.jsx                # Root component, routing, region selector
│       ├── services/api.js        # Axios client for all backend endpoints
│       ├── pages/
│       │   ├── Dashboard.jsx      # Main overview — KPIs, charts, zone map
│       │   ├── DemoPage.jsx       # Animated live demo with wow-moment panel
│       │   ├── MCPAgentPage.jsx   # PandemicMCPAgent natural language interface
│       │   ├── SimulationPage.jsx # SEIR model runner with configurable parameters
│       │   ├── ScenarioPage.jsx   # Side-by-side what-if comparison
│       │   ├── AgentsPage.jsx     # Multi-agent pipeline visualization
│       │   ├── NLQueryPage.jsx    # Chat-style natural language query interface
│       │   └── RegionsPage.jsx    # Region database browser
│       └── components/
│           └── Map/RegionMap.jsx  # Leaflet map with colour-coded zone risk circles
│
├── data/sample/pandemic_data.json # Reference disease parameters and intervention data
├── scripts/setup.sh               # One-shot local setup script
└── docker-compose.yml
```

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### One-Command Setup

```bash
bash scripts/setup.sh
```

### Manual Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

API available at: `http://localhost:8080`
Swagger docs: `http://localhost:8080/api/docs`

### Manual Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at: `http://localhost:3000`

### Docker (Full Stack)

```bash
docker-compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

### Optional: Enable Gemini LLM

The system works fully without an LLM key — all features are available via analytical fallback models. To enable Gemini 2.5 Pro reasoning:

1. Get a free key at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Add it to `backend/.env`:

```env
GEMINI_API_KEY=your-key-here
```

---

## API Reference

### Simulation

**POST `/api/simulate`** — Run a single SEIR simulation

```json
{
  "region_id": "delhi",
  "days": 180,
  "intervention": "partial_lockdown"
}
```

**GET `/api/simulate/parameters/{region_id}`** — Get derived SEIR parameters for a region

**GET `/api/simulate/history/{region_id}`** — Recent simulation runs from the database

---

### Scenarios

**POST `/api/scenario`** — Run multiple scenarios simultaneously for comparison

```json
{
  "region_id": "delhi",
  "days": 180,
  "interventions": ["no_action", "full_lockdown", "vaccination_rollout"]
}
```

**GET `/api/scenario/interventions`** — List all valid intervention identifiers

---

### Agents

**POST `/api/agents/analyze`** — Run the full 4-agent multi-agent analysis pipeline

```json
{
  "region_id": "delhi",
  "days": 180,
  "intervention": "no_action",
  "run_all_scenarios": true
}
```

**GET `/api/agents/status`** — Current agent and service status

---

### MCP Agent

**POST `/mcp-agent`** — Natural language query processed by PandemicMCPAgent

```json
{
  "query": "What is the impact of a full lockdown in Delhi?"
}
```

**GET `/mcp-agent/schema`** — MCP tool schema for `simulate_pandemic`

---

### Predictions & Recommendations

**POST `/api/predict`** — Infection forecasts and key metrics via Prediction Agent

**POST `/api/recommend`** — Policy recommendations via Policy Recommendation Agent

---

### Regions

**GET `/api/regions`** — List all available regions

**GET `/api/regions/{region_id}`** — Region detail including zones, weather, and disease stats

**GET `/api/regions/{region_id}/historical`** — 90-day historical disease data

---

### RAG / Knowledge Base

**POST `/api/rag/query`** — Direct vector search against the pandemic knowledge base

**POST `/api/rag/nl-query`** — Natural language question answered with RAG + LLM

**GET `/api/rag/documents`** — List all knowledge base documents

---

### Real-Time Data

**GET `/api/realtime/{region_id}`** — Aggregate live weather, disease stats, AQI, and mobility

**GET `/api/realtime/{region_id}/weather`** — Live weather only

**GET `/api/realtime/{region_id}/disease`** — Live disease stats only

---

### Economics

**POST `/api/economics/analyze`** — Cost-benefit analysis across intervention scenarios

**GET `/api/economics/summary/{region_id}`** — Quick economic summary with default interventions

---

### Adaptive Learning

**GET `/api/adaptive/insights/{region_id}`** — AI-learned insights from simulation history

**GET `/api/adaptive/policy-rankings/{region_id}`** — Intervention rankings from historical runs + RAG

---

### Health

**GET `/health`** — Simple health check (required by Cloud Run)

**GET `/api/health`** — Full service status with component availability

---

## Intervention Strategies

| ID | Display Name | Transmission Reduction | Mobility Reduction | Economic Cost |
|---|---|---|---|---|
| `no_action` | No Intervention | 0% | 0% | 0% GDP |
| `partial_lockdown` | Partial Lockdown | 40% | 30% | 3.5% GDP/day |
| `full_lockdown` | Full Lockdown | 75% | 70% | 8.5% GDP/day |
| `vaccination_rollout` | Vaccination Rollout | 65% | 10% | 0.5% GDP/day |
| `combined_strategy` | Combined Strategy | 80% | 50% | 4.0% GDP/day |
| `school_closure` | School Closures | 25% | 20% | 1.8% GDP/day |
| `travel_restriction` | Travel Restrictions | 30% | 40% | 2.5% GDP/day |

---

## Multi-Agent Pipeline

### Agent 1 — Prediction Agent

Forecasts infection trajectories using SEIR model output. Outputs R0, peak day, attack rate, severity classification, weekly projections, and healthcare capacity breach estimates.

### Agent 2 — Risk Analysis Agent

Scores each intra-city zone using a composite risk model weighted across population density, mobility index, healthcare deficit, vulnerable population percentage, and current case burden. Generates zone alerts and risk distribution summaries.

### Agent 3 — Policy Recommendation Agent

Evaluates all six intervention strategies against severity-weighted criteria. Produces ranked policies with cost-benefit ratios, a phased implementation plan, and urgency classification. Enriched with RAG evidence and optional Gemini LLM reasoning.

### Agent 4 — Simulation Agent

Runs what-if scenario comparison across all intervention types. Computes infection reduction percentages, lives saved, peak delay, and sensitivity ranges. Identifies the best scenario and generates actionable what-if insights.

### Orchestrator

Runs Prediction and Risk agents in parallel (Phase 1), feeds outputs to Policy agent (Phase 2), feeds all three to Simulation agent (Phase 3), then synthesizes a unified recommendation with per-agent confidence scores.

---

## MCP Agent (PandemicMCPAgent)

The `PandemicMCPAgent` implements the **Google Agent Development Kit (ADK)** pattern with **Model Context Protocol (MCP)**:

- **One agent** — `PandemicMCPAgent`
- **One MCP tool** — `simulate_pandemic`
- **One external data source** — the SEIR simulation engine

**Flow:**

1. Receive natural language query (e.g. *"What happens with a lockdown in Tokyo?"*)
2. `IntentParser` extracts region and intervention intent
3. Agent calls `simulate_pandemic` MCP tool → receives structured JSON data
4. Gemini LLM (or analytical template) generates a natural language response from the data

The agent is accessible via the `/mcp-agent` REST endpoint and visualized in the **MCP Agent** page of the dashboard, which shows the full execution flow, parsed intent, raw tool output, and natural language response side by side.

---

## RAG Knowledge Base

The system includes a **FAISS-backed vector knowledge base** built from 13 pandemic research documents covering:

- Full lockdown effectiveness (Wuhan 2020)
- Partial lockdown — UK Tier system
- mRNA vaccine effectiveness (Israel 2021)
- Vaccination rollout (South Korea 2021)
- School closure impact (UK SAGE modelling)
- Travel restrictions (New Zealand 2020)
- Layered NPI strategy (Taiwan 2020–2021)
- Targeted zone restrictions (Germany 2020)
- High-density transmission (Mumbai Dharavi 2020)
- Healthcare surge capacity (Italy 2020)
- Vaccination + NPI synergy (Portugal 2021)
- Reproduction numbers by pathogen (WHO 2022)
- Early intervention advantage (meta-analysis 2021)

Embeddings are computed locally using a **deterministic TF-IDF vectorizer** — no external embedding API required. The RAG service provides context injection for LLM prompts and evidence grounding for policy recommendations.

---

## Real-Time Data Sources

All APIs are free and require no authentication keys:

| Data | Source | Cache TTL |
|---|---|---|
| Weather (temperature, humidity, wind, UV) | Open-Meteo API | 15 minutes |
| Air Quality Index (PM2.5, PM10, US AQI) | Open-Meteo Air Quality API | 30 minutes |
| COVID-19 disease statistics | disease.sh API | 60 minutes |
| Mobility indices | Oxford OxCGRT-calibrated model | Computed per-request |

All services include deterministic analytical fallbacks that activate automatically when external APIs are unreachable, so the system never fails in offline or test environments.

---

## Economic Model

The economic model computes real dollar costs and WHO cost-effectiveness metrics for each intervention:

- **GDP loss** per intervention type (Oxford Economic Impact Study 2022 coefficients)
- **Hospital bed and ICU costs** based on 4% and 0.8% hospitalization rates
- **Vaccine dose costs** ($15/dose average including delivery)
- **Testing and contact tracing costs** per case
- **Cost per life saved** (ICER) and **cost per DALY averted**
- **WHO threshold check**: cost-effective if cost/DALY < 3× regional GDP per capita
- **Resource timeline**: daily bed/ICU/ventilator requirements over the simulation period

---

## Adaptive Learning

The `AdaptiveLearningService` reads from the simulation history database to:

- **Adapt SEIR parameters**: nudge `beta` toward historically observed values (up to ±15%)
- **Rank interventions**: combine observed peak infections with RAG effectiveness scores
- **Calibrate confidence**: agents gain or lose confidence based on volume of historical data
- **Surface insights**: detect worsening trends, identify best-performing interventions per region

---

## Supported Regions

| ID | Name | Country | Population | Notes |
|---|---|---|---|---|
| `delhi` | Delhi NCR | India | 32.9M | 8 intra-city zones |
| `mumbai` | Mumbai Metropolitan | India | 21.3M | 6 zones including Dharavi |
| `new_york` | New York City | USA | 8.3M | 5 boroughs |
| `london` | Greater London | UK | 9.6M | 6 zones |
| `tokyo` | Tokyo Metropolis | Japan | 13.9M | 6 zones including Tama |
| `sao_paulo` | Sao Paulo | Brazil | 22.0M | 6 zones |

Each region includes zone-level data for population, density, mobility index, hospital beds per 1,000, elderly population percentage, and current case estimates.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Epidemiological Model | SEIR (scipy.integrate.odeint) |
| AI Agents | Python async coroutines + AgentOrchestrator |
| MCP Agent | PandemicMCPAgent (ADK pattern + MCP protocol) |
| LLM | Gemini 2.5 Pro (REST API) — optional; analytical fallback included |
| RAG | FAISS (IndexFlatIP) + local TF-IDF embedder |
| Backend | FastAPI 0.109 + Uvicorn |
| Database | SQLAlchemy async — SQLite (dev) / PostgreSQL (prod) |
| Frontend | React 18 + Vite |
| Charts | Recharts |
| Maps | Leaflet + react-leaflet |
| Weather API | Open-Meteo (free, no key) |
| Disease API | disease.sh (free, no key) |
| Deployment | Docker + nginx |

---

## Demo Flow

1. Open `http://localhost:3000`
2. **Dashboard** loads Delhi NCR with live simulation — observe R0, active cases, zone risk map, and AI recommendation
3. Navigate to **Live Demo** — click "Run Demo" to watch the animated scenario comparison
4. The **WOW moment panel** shows the human cost difference between no action and the best intervention in real numbers (infections, deaths, lives saved)
5. Navigate to **MCP Agent** — type a natural language question and watch the agent parse intent, call the MCP tool, retrieve structured data, and generate a response
6. Navigate to **Scenarios** — select interventions and compare outcomes side-by-side
7. Navigate to **AI Agents** — run the full 4-agent orchestration and inspect each agent's reasoning, confidence, and recommendations
8. Navigate to **NL Query** — ask plain English questions answered by live SEIR simulations

---

## Deployment

### Google Cloud Run

```bash
# Backend
gcloud run deploy pandemic-twin-backend \
  --source ./backend \
  --port 8080 \
  --region us-central1

# Frontend
gcloud run deploy pandemic-twin-frontend \
  --source ./frontend \
  --port 8080 \
  --region us-central1
```

### Environment Variables

```env
# Backend (.env)
API_HOST=0.0.0.0
PORT=8080
DEBUG=false
GEMINI_API_KEY=              # Optional — enables Gemini 2.5 Pro LLM reasoning
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/pandemic_twin
```

```env
# Frontend (.env)
VITE_API_URL=                # Leave empty to use Vite proxy / nginx proxy
```

---

## Extending to Production

To replace mock or estimated data with real production sources:

1. **Weather** — `get_weather_data()` in `data_service.py` already calls Open-Meteo live; no change needed
2. **Disease statistics** — `get_current_disease_stats()` already calls disease.sh live; replace with WHO API or national health dashboard for regional granularity
3. **Mobility** — Integrate Google Mobility Reports CSV download in `get_mobility_data()`
4. **Historical data** — Import from Kaggle COVID-19 datasets or connect to a time-series database
5. **LLM** — Set `GEMINI_API_KEY` env var; swap `GEMINI_MODEL` constant in `llm_service.py` to use a different model
6. **Database** — Set `DATABASE_URL` to a PostgreSQL connection string for multi-instance persistence
7. **RAG corpus** — Add documents to `PANDEMIC_KNOWLEDGE_BASE` in `rag_service.py`; the FAISS index rebuilds on startup
8. **Regions** — Add entries to `DataIngestionService.REGIONS` in `data_service.py` and zone templates in `_generate_zones()`

---

## License

MIT License — Free for academic and research use.
