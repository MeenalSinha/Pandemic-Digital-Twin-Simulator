"""
Pandemic Digital Twin Simulator v3.0 — Backend API

Layers:
  Routes          → HTTP, validation
  Services        → DataIngestion, RealTime, LLM, RAG, DB, Economic, Adaptive
  Models          → SEIR ODE solver
  Agents          → 4-agent orchestration (Prediction/Risk/Policy/Simulation)
                    + PandemicMCPAgent (MCP-compliant single agent)
"""

import os, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database
    from services.db_service import db
    await db.init_db()

    # RAG warm-up (builds FAISS index)
    from services.rag_service import PandemicKnowledgeBase
    PandemicKnowledgeBase.get_instance()
    logger.info("RAG knowledge base ready")

    # LLM
    from services.llm_service import get_llm_service
    get_llm_service()

    # Real-time service
    from services.realtime_service import get_realtime_service
    get_realtime_service()

    # Economic model
    from services.economic_model import get_economic_model
    get_economic_model()

    # MCP Agent (pre-warm)
    from agents.mcp_agent import get_mcp_agent
    get_mcp_agent()
    logger.info("PandemicMCPAgent ready")

    logger.info("All services initialised — system ready")
    yield
    logger.info("Shutdown complete")


app = FastAPI(
    title="Pandemic Digital Twin Simulator",
    description=(
        "AI-powered epidemic simulation: SEIR ODE + 4-agent orchestration + "
        "MCP agent (PandemicMCPAgent) + RAG knowledge base + LLM reasoning + "
        "real-time APIs + economic model + adaptive learning."
    ),
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — wide-open for Cloud Run deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,          # must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────
from routes.simulate  import router as simulate_router
from routes.predict   import router as predict_router
from routes.recommend import router as recommend_router
from routes.scenario  import router as scenario_router
from routes.regions   import router as regions_router
from routes.agents    import router as agents_router
from routes.rag       import router as rag_router
from routes.realtime  import router as realtime_router
from routes.economics import router as economics_router
from routes.adaptive  import router as adaptive_router
from routes.mcp_agent import router as mcp_agent_router

app.include_router(simulate_router,   prefix="/api/simulate",   tags=["Simulation"])
app.include_router(predict_router,    prefix="/api/predict",    tags=["Prediction"])
app.include_router(recommend_router,  prefix="/api/recommend",  tags=["Recommendations"])
app.include_router(scenario_router,   prefix="/api/scenario",   tags=["Scenarios"])
app.include_router(regions_router,    prefix="/api/regions",    tags=["Regions"])
app.include_router(agents_router,     prefix="/api/agents",     tags=["Agents"])
app.include_router(rag_router,        prefix="/api/rag",        tags=["RAG / Knowledge"])
app.include_router(realtime_router,   prefix="/api/realtime",   tags=["Real-Time Data"])
app.include_router(economics_router,  prefix="/api/economics",  tags=["Economics"])
app.include_router(adaptive_router,   prefix="/api/adaptive",   tags=["Adaptive Learning"])
app.include_router(mcp_agent_router,  prefix="/api/mcp-agent",  tags=["MCP Agent"])


# ── Health check (required by Cloud Run) ──────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    """Simple health check for Cloud Run / load balancers."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Pandemic Digital Twin Simulator",
        "version": "3.0.0",
        "status": "operational",
        "docs": "/api/docs",
        "mcp_agent": "/api/mcp-agent",
        "health": "/health",
    }


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    from services.llm_service import get_llm_service
    llm = get_llm_service()
    return {
        "status":   "healthy",
        "version":  "3.0.0",
        "services": {
            "seir_model":        "active",
            "agents":            "active (4-agent pipeline)",
            "mcp_agent":         "active (PandemicMCPAgent + simulate_pandemic tool)",
            "rag":               "active (FAISS, 13 documents)",
            "llm":               "gemini-2.5-pro (active)" if llm._has_llm else "analytical-fallback",
            "database":          "active (SQLite/PostgreSQL)",
            "realtime_apis":     "active (Open-Meteo + disease.sh)",
            "economic_model":    "active",
            "adaptive_learning": "active",
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", os.getenv("API_PORT", "8080"))),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        workers=1,
    )
