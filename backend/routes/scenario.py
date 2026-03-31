"""Scenario (What-If Analysis) Routes — with RAG evidence and DB persistence."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

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
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scenario-worker")


class ScenarioRequest(BaseModel):
    region_id: str = Field(default="delhi")
    days: int = Field(default=180, ge=30, le=365)
    interventions: List[str] = Field(
        default=["no_action", "partial_lockdown", "full_lockdown", "vaccination_rollout"]
    )

    @field_validator("region_id")
    @classmethod
    def validate_region_id(cls, v: str) -> str:
        valid = set(DataIngestionService.REGIONS.keys())
        if v.lower().strip() not in valid:
            raise ValueError(f"Unknown region '{v}'. Available: {sorted(valid)}")
        return v.lower().strip()

    @field_validator("interventions")
    @classmethod
    def validate_interventions(cls, v: List[str]) -> List[str]:
        invalid = [iv for iv in v if iv not in SEIRModel.VALID_INTERVENTIONS]
        if invalid:
            raise ValueError(f"Unknown interventions: {invalid}. Valid: {sorted(SEIRModel.VALID_INTERVENTIONS)}")
        if len(v) < 1:
            raise ValueError("At least one intervention required.")
        return v


def _run_scenarios_sync(region_id, days, interventions):
    region = data_service.get_region(region_id)
    weather = data_service.get_weather_data(region)
    disease_stats = data_service.get_current_disease_stats(region)
    param_dict = data_service.get_seir_parameters(region, disease_stats, weather)

    scenario_results = {}
    for iv in interventions:
        params = SEIRParameters(**param_dict)
        params = SEIRModel.apply_intervention(params, iv)
        result = SEIRModel(params).run(days=days)
        result.scenario_name = iv
        scenario_results[iv] = result.to_dict()

    return {"region": region, "weather": weather,
            "disease_stats": disease_stats, "scenario_results": scenario_results}


@router.post("")
async def run_scenarios(request: ScenarioRequest):
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            _executor, _run_scenarios_sync,
            request.region_id, request.days, request.interventions,
        )
        scenario_results = data["scenario_results"]
        region = data["region"]
        baseline = scenario_results.get("no_action") or next(iter(scenario_results.values()))
        baseline_infected = baseline.get("total_infected", 1)
        baseline_deceased = baseline.get("total_deceased", 0)

        comparisons = []
        for iv, result in scenario_results.items():
            reduction = ((baseline_infected - result["total_infected"]) / max(1, baseline_infected)) * 100
            lives_saved = round(baseline_deceased - result["total_deceased"])
            comparisons.append({
                "scenario": iv,
                "display_name": iv.replace("_", " ").title(),
                "total_infected": result["total_infected"],
                "peak_infected": result["peak_infected"],
                "peak_day": result["peak_day"],
                "total_deceased": result["total_deceased"],
                "epidemic_end_day": result.get("epidemic_end_day"),
                "reduction_vs_baseline_pct": round(reduction, 1),
                "lives_saved": max(0, lives_saved),
                "r0": result["r0"],
                "basic_r0": result.get("basic_r0"),
            })
        comparisons.sort(key=lambda x: x["total_infected"])

        best = comparisons[0]

        # RAG evidence for best scenario
        llm = get_llm_service()
        evidence = llm._kb.get_policy_evidence(best["scenario"], best["r0"] or 1.5)
        rag_context = [{"title": r.title, "effectiveness": r.effectiveness,
                        "similarity": r.similarity_score} for r in evidence]

        # Simulation agent insights
        orchestrator = AgentOrchestrator()
        sim_result = await orchestrator.simulation_agent.analyze({
            "region": region, "simulation_result": baseline,
            "weather_data": data["weather"], "disease_stats": data["disease_stats"],
            "scenario_results": scenario_results,
        })

        # Persist
        asyncio.create_task(db.save_scenario_comparison(
            request.region_id, best["scenario"],
            best["reduction_vs_baseline_pct"], best["lives_saved"], comparisons
        ))

        return {
            "success": True,
            "region": {"id": region["id"], "name": region["name"], "population": region["population"]},
            "scenarios": scenario_results,
            "comparisons": comparisons,
            "best_scenario": best,
            "simulation_analysis": sim_result.output,
            "rag_evidence": rag_context,
            "agent_reasoning": sim_result.reasoning,
            "agent_recommendations": sim_result.recommendations,
        }
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Scenario error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interventions")
async def list_interventions():
    return {
        "interventions": {
            "no_action":           {"display": "No Intervention",     "description": "Epidemic runs its natural course"},
            "partial_lockdown":    {"display": "Partial Lockdown",    "description": "Restrict movement by 40%"},
            "full_lockdown":       {"display": "Full Lockdown",       "description": "Complete movement restriction"},
            "vaccination_rollout": {"display": "Vaccination Rollout", "description": "Accelerated vaccination campaign"},
            "combined_strategy":   {"display": "Combined Strategy",   "description": "Targeted lockdown + vaccination + surveillance"},
            "school_closure":      {"display": "School Closures",     "description": "Close all educational institutions"},
            "travel_restriction":  {"display": "Travel Restrictions", "description": "Restrict inter-zone travel"},
        }
    }
