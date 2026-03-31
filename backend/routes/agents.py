"""Agents Route — with RAG + LLM + DB persistence."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from models.seir_model import SEIRModel, SEIRParameters
from services.data_service import DataIngestionService
from services.db_service import db
from services.llm_service import get_llm_service
from agents.orchestrator import AgentOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)
data_service = DataIngestionService()
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-worker")


class AgentAnalysisRequest(BaseModel):
    region_id: str = Field(default="delhi")
    days: int = Field(default=180, ge=30, le=365)
    intervention: str = Field(default="no_action")
    run_all_scenarios: bool = Field(default=True)

    @field_validator("intervention")
    @classmethod
    def validate_intervention(cls, v: str) -> str:
        if v not in SEIRModel.VALID_INTERVENTIONS:
            raise ValueError(f"Unknown intervention '{v}'.")
        return v

    @field_validator("region_id")
    @classmethod
    def validate_region_id(cls, v: str) -> str:
        valid = set(DataIngestionService.REGIONS.keys())
        if v.lower().strip() not in valid:
            raise ValueError(f"Unknown region '{v}'.")
        return v.lower().strip()


def _build_simulation_data(region_id, days, intervention, run_all_scenarios):
    region = data_service.get_region(region_id)
    weather = data_service.get_weather_data(region)
    disease_stats = data_service.get_current_disease_stats(region)
    mobility_data = data_service.get_mobility_data(region)
    param_dict = data_service.get_seir_parameters(region, disease_stats, weather)

    params = SEIRParameters(**param_dict)
    params = SEIRModel.apply_intervention(params, intervention)
    primary = SEIRModel(params).run(days=days)
    primary.scenario_name = intervention

    scenario_results = {}
    if run_all_scenarios:
        for iv in ["no_action", "partial_lockdown", "full_lockdown",
                   "vaccination_rollout", "combined_strategy"]:
            p = SEIRParameters(**param_dict)
            p = SEIRModel.apply_intervention(p, iv)
            r = SEIRModel(p).run(days=days)
            r.scenario_name = iv
            scenario_results[iv] = r.to_dict()

    return {
        "region": region,
        "simulation_result": primary.to_dict(),
        "weather_data": weather,
        "disease_stats": disease_stats,
        "scenario_results": scenario_results,
        "mobility_data": mobility_data,
    }


@router.post("/analyze")
async def run_agent_analysis(request: AgentAnalysisRequest):
    try:
        loop = asyncio.get_running_loop()
        agent_data = await loop.run_in_executor(
            _executor, _build_simulation_data,
            request.region_id, request.days,
            request.intervention, request.run_all_scenarios,
        )

        # Multi-agent pipeline
        orchestrator = AgentOrchestrator()
        full_analysis = await orchestrator.run_full_analysis(agent_data)
        synthesis = full_analysis["synthesis"]

        # LLM-powered policy reasoning with RAG
        llm = get_llm_service()
        policy_out = full_analysis["agents"]["policy"]["output"]
        primary_rec = policy_out.get("primary_recommendation", {})
        pred_out = full_analysis["agents"]["prediction"]["output"]

        llm_result = llm.generate_policy_recommendation(
            region_name=agent_data["region"]["name"],
            severity=synthesis.get("overall_severity", "MODERATE"),
            r0=synthesis.get("key_metrics", {}).get("r0", 1.5),
            top_policy=primary_rec.get("name", "Monitor Situation"),
            high_risk_zones=synthesis.get("key_metrics", {}).get("high_risk_zones", 0),
            capacity_breach_day=pred_out.get("capacity_breach_day"),
        )

        # Inject LLM reasoning into policy agent output
        full_analysis["agents"]["policy"]["llm_reasoning"] = llm_result["reasoning"]
        full_analysis["agents"]["policy"]["llm_source"] = llm_result["source"]
        full_analysis["agents"]["policy"]["rag_evidence"] = llm_result["evidence"]

        # RAG: similar historical outbreaks
        rag_outbreaks = llm._kb.get_similar_outbreaks(
            r0=synthesis.get("key_metrics", {}).get("r0", 1.5),
            severity=synthesis.get("overall_severity", "MODERATE"),
            region_density=agent_data["region"].get("density", 5000),
        )
        full_analysis["rag_similar_outbreaks"] = [
            {"id": r.id, "title": r.title,
             "effectiveness": r.effectiveness, "content": r.content[:200]}
            for r in rag_outbreaks
        ]

        # Persist
        asyncio.create_task(db.save_agent_analysis(request.region_id, synthesis))

        sim = agent_data["simulation_result"]
        return {
            "success": True,
            "region": {
                "id": agent_data["region"]["id"],
                "name": agent_data["region"]["name"],
                "population": agent_data["region"]["population"],
            },
            "analysis": full_analysis,
            "simulation_summary": {
                "r0": sim["r0"],
                "basic_r0": sim.get("basic_r0"),
                "peak_day": sim["peak_day"],
                "peak_infected": sim["peak_infected"],
                "total_infected": sim["total_infected"],
            },
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Agent analysis error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agents_status():
    llm_available = bool(__import__("os").getenv("ANTHROPIC_API_KEY"))
    return {
        "agents": [
            {"name": "Prediction Agent",             "description": "Forecasts infection spread trajectories"},
            {"name": "Risk Analysis Agent",          "description": "Identifies and ranks high-risk zones"},
            {"name": "Policy Recommendation Agent",  "description": "Recommends optimal intervention strategies"},
            {"name": "Simulation Agent",             "description": "What-if scenario comparison"},
        ],
        "orchestrator": "active",
        "rag": "active (FAISS + TF-IDF, 13 pandemic knowledge documents)",
        "llm": f"{'active (Claude)' if llm_available else 'fallback (analytical model)'}",
        "database": "active (SQLite dev / PostgreSQL prod)",
        "valid_interventions": sorted(SEIRModel.VALID_INTERVENTIONS),
    }
