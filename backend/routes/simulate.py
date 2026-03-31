"""Simulation Routes — with database persistence and LLM interpretation."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from services.realtime_service import get_realtime_service
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from models.seir_model import SEIRModel, SEIRParameters
from services.data_service import DataIngestionService
from services.db_service import db
from services.llm_service import get_llm_service

router = APIRouter()
logger = logging.getLogger(__name__)
data_service = DataIngestionService()
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="seir-worker")


class SimulateRequest(BaseModel):
    region_id: str = Field(default="delhi")
    days: int = Field(default=180, ge=30, le=365)
    intervention: str = Field(default="no_action")
    custom_beta: Optional[float] = Field(default=None, ge=0.01, le=2.0)
    custom_gamma: Optional[float] = Field(default=None, ge=0.01, le=1.0)

    @field_validator("intervention")
    @classmethod
    def validate_intervention(cls, v: str) -> str:
        if v not in SEIRModel.VALID_INTERVENTIONS:
            raise ValueError(f"Unknown intervention '{v}'. Valid: {sorted(SEIRModel.VALID_INTERVENTIONS)}")
        return v

    @field_validator("region_id")
    @classmethod
    def validate_region_id(cls, v: str) -> str:
        valid = set(DataIngestionService.REGIONS.keys())
        if v.lower().strip() not in valid:
            raise ValueError(f"Unknown region '{v}'. Available: {sorted(valid)}")
        return v.lower().strip()


def _run_simulation_sync(region_id, days, intervention, custom_beta, custom_gamma):
    region = data_service.get_region(region_id)
    weather = get_realtime_service().get_live_weather(region_id)
    disease_stats = data_service.get_current_disease_stats(region)
    param_dict = data_service.get_seir_parameters(region, disease_stats, weather)
    params = SEIRParameters(**param_dict)

    if custom_beta is not None:
        params.beta = custom_beta
    if custom_gamma is not None:
        params.gamma = custom_gamma

    params = SEIRModel.apply_intervention(params, intervention)
    result = SEIRModel(params).run(days=days)
    result.scenario_name = intervention

    return {
        "region": region, "weather_data": weather,
        "disease_stats": disease_stats,
        "simulation_result": result.to_dict(),
        "params": {
            "beta": params.beta, "sigma": params.sigma, "gamma": params.gamma,
            "mu": params.mu, "intervention_factor": params.intervention_factor,
            "vaccine_rate": params.vaccine_rate, "temperature_factor": params.temperature_factor,
            "mobility_factor": params.mobility_factor,
        },
    }


@router.post("")
async def run_simulation(request: SimulateRequest):
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            _executor, _run_simulation_sync,
            request.region_id, request.days, request.intervention,
            request.custom_beta, request.custom_gamma,
        )

        sim = data["simulation_result"]
        region = data["region"]

        # LLM interpretation (non-blocking)
        llm = get_llm_service()
        pred_output = sim
        llm_result = llm.interpret_simulation(
            region_name=region["name"],
            r0=sim["r0"],
            severity=("CRITICAL" if sim["r0"] > 2.5 else "HIGH" if sim["r0"] > 1.5 else "MODERATE"),
            peak_infected=sim["peak_infected"],
            peak_day=sim["peak_day"],
            attack_rate=(sim["total_infected"] / region["population"]) * 100,
            population=region["population"],
        )

        # Persist to DB (fire-and-forget)
        asyncio.create_task(db.save_simulation(
            request.region_id, request.intervention, request.days,
            sim, data["params"]
        ))
        asyncio.create_task(db.save_region_snapshot(
            request.region_id, data["disease_stats"], data["weather_data"]
        ))

        return {
            "success": True,
            "region": region,
            "weather_data": data["weather_data"],
            "disease_stats": data["disease_stats"],
            "simulation_result": sim,
            "parameters_used": data["params"],
            "llm_interpretation": llm_result,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Simulation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/{region_id}")
async def get_simulation_parameters(region_id: str):
    try:
        region = data_service.get_region(region_id)
        weather = get_realtime_service().get_live_weather(region_id)
        disease_stats = data_service.get_current_disease_stats(region)
        params = data_service.get_seir_parameters(region, disease_stats, weather)
        return {"region_id": region_id, "parameters": params}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/interventions")
async def list_interventions():
    return {"interventions": sorted(SEIRModel.VALID_INTERVENTIONS)}


@router.get("/history/{region_id}")
async def simulation_history(region_id: str):
    """Return recent simulation runs for a region from the database."""
    history = await db.get_recent_simulations(region_id)
    return {"region_id": region_id, "history": history}
