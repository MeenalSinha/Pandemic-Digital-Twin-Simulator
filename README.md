# Pandemic Digital Twin Simulator

An AI-powered, end-to-end system that simulates disease spread in real time and recommends optimal public health interventions using a multi-agent architecture.

---

## Table of Contents

1. [Overview](#overview)
2. [Folder Structure](#folder-structure)
3. [Architecture](#architecture)
4. [Setup Instructions](#setup-instructions)
5. [API Reference](#api-reference)
6. [Demo Flow](#demo-flow)
7. [Tech Stack](#tech-stack)
8. [Deployment](#deployment)

---

## Overview

The Pandemic Digital Twin Simulator creates a computational replica of a real-world region and models disease dynamics using a hybrid SEIR epidemiological model enhanced by a four-agent AI orchestration system. It is designed for autonomous decision-making, not conversational interaction.

Key capabilities:

- SEIR compartmental model with real-world parameter derivation
- Four specialized AI agents: Prediction, Risk Analysis, Policy Recommendation, Simulation
- Interactive what-if scenario analysis across 7 intervention strategies
- Zone-level risk heatmap with geographic visualization
- Cost-benefit analysis of all policy options
- Alert system for high-risk zones
- Multi-region comparison across 6 global cities

---

## Folder Structure

```
pandemic-digital-twin/
├── backend/                     # FastAPI backend
│   ├── main.py                  # App entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── agents/
│   │   └── orchestrator.py      # Multi-agent system (all 4 agents)
│   ├── models/
│   │   └── seir_model.py        # SEIR epidemiological model
│   ├── routes/
│   │   ├── simulate.py          # POST /api/simulate
│   │   ├── predict.py           # POST /api/predict
│   │   ├── recommend.py         # POST /api/recommend
│   │   ├── scenario.py          # POST /api/scenario
│   │   ├── regions.py           # GET /api/regions
│   │   └── agents.py            # POST /api/agents/analyze
│   ├── services/
│   │   └── data_service.py      # Data ingestion & mock APIs
│   └── utils/
│
├── frontend/                    # React + Vite frontend
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── App.jsx              # Root component + routing
│       ├── App.css              # Layout styles
│       ├── index.css            # Global design system
│       ├── main.jsx
│       ├── services/
│       │   └── api.js           # Axios API client
│       ├── pages/
│       │   ├── Dashboard.jsx    # Main overview page
│       │   ├── SimulationPage.jsx   # SEIR model runner
│       │   ├── ScenarioPage.jsx     # What-if analysis
│       │   ├── AgentsPage.jsx       # Multi-agent visualization
│       │   └── RegionsPage.jsx      # Region database
│       └── components/
│           └── Map/
│               └── RegionMap.jsx    # Leaflet map component
│
├── data/
│   └── sample/
│       └── pandemic_data.json   # Sample disease + intervention data
│
├── docs/                        # Documentation
├── scripts/                     # Setup scripts
├── docker-compose.yml
└── README.md
```

---

## Architecture

### Data Flow

```
Real-World APIs (Weather, Mobility, Population)
         |
    Data Ingestion Service
         |
    SEIR Epidemiological Model
         |
    Multi-Agent Orchestrator
    ├── Prediction Agent  ──┐
    ├── Risk Analysis Agent  ├──> Shared State ──> Synthesis
    ├── Policy Rec. Agent   ┘
    └── Simulation Agent (What-If)
         |
    FastAPI REST Layer
         |
    React Dashboard
```

### Multi-Agent Communication

Agents run in an async pipeline:
1. Prediction Agent + Risk Agent run in parallel
2. Policy Agent receives both outputs
3. Simulation Agent receives all three outputs
4. Orchestrator synthesizes a unified recommendation

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API will be available at: http://localhost:8000
Swagger docs: http://localhost:8000/api/docs

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Dashboard will be available at: http://localhost:3000

### Docker (Full Stack)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## API Reference

### POST /api/simulate
Run SEIR simulation for a region with a given intervention.

```json
{
  "region_id": "delhi",
  "days": 180,
  "intervention": "partial_lockdown"
}
```

### POST /api/scenario
Run multiple scenarios simultaneously for comparison.

```json
{
  "region_id": "delhi",
  "days": 180,
  "interventions": ["no_action", "full_lockdown", "vaccination_rollout"]
}
```

### POST /api/agents/analyze
Run the full 4-agent multi-agent analysis pipeline.

```json
{
  "region_id": "delhi",
  "days": 180,
  "run_all_scenarios": true
}
```

### POST /api/recommend
Get AI policy recommendations for a region.

### POST /api/predict
Get infection forecasts and key metrics.

### GET /api/regions
List all available regions.

### GET /api/regions/{region_id}
Get detailed data for a specific region including weather, stats, and zones.

---

## Intervention Types

| ID | Description | Transmission Reduction |
|---|---|---|
| no_action | No intervention | 0% |
| partial_lockdown | Restrict movement by 40% | 40% |
| full_lockdown | Full movement restriction | 75% |
| vaccination_rollout | Accelerated vaccination | 65% |
| combined_strategy | Targeted lockdown + vaccination | 80% |
| school_closure | Close educational institutions | 25% |
| travel_restriction | Restrict inter-zone travel | 30% |

---

## Demo Flow

1. Open http://localhost:3000
2. Dashboard loads Delhi NCR with live simulation
3. Observe current metrics: R0, active cases, risk zones, AI recommendation
4. Navigate to Scenarios — run all interventions simultaneously
5. Compare: No Action shows case spike; Full Lockdown shows 75% reduction
6. Navigate to AI Agents — trigger full multi-agent orchestration
7. Observe each agent's reasoning, confidence, and recommendations
8. Synthesis panel shows consensus: best strategy with justification

---

## Tech Stack

| Layer | Technology |
|---|---|
| Epidemiological Model | SEIR (scipy.integrate.odeint) |
| AI Agents | Python async coroutines + orchestration |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18 + Vite |
| Charts | Recharts |
| Maps | Leaflet + React-Leaflet |
| Deployment | Docker + nginx |
| Data | Realistic mock APIs (production-ready to swap) |

---

## Deployment

### Google Cloud Run

```bash
# Backend
gcloud run deploy pandemic-twin-backend \
  --source ./backend \
  --port 8000 \
  --region us-central1

# Frontend
gcloud run deploy pandemic-twin-frontend \
  --source ./frontend \
  --port 80 \
  --region us-central1
```

### Environment Variables

```env
# Backend (.env)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend (.env)
VITE_API_URL=http://localhost:8000
```

---

## Extending to Production

To replace mock data with real APIs:

1. Weather: Replace `get_weather_data()` in `data_service.py` with OpenWeatherMap API
2. Mobility: Integrate Google Mobility Reports CSV download
3. Disease Stats: Connect to WHO API or national health dashboards
4. Historical Data: Import from Kaggle COVID-19 datasets
5. Vector DB: Add FAISS or pgvector for RAG over policy documents

---

## License

MIT License — Free for academic and research use.
