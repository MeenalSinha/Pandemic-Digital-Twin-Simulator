"""Economics Routes — cost-benefit analysis, resource allocation, ROI."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from models.seir_model import SEIRModel, SEIRParameters
from services.data_service import DataIngestionService
from services.realtime_service import get_realtime_service
from services.economic_model import get_economic_model

router = APIRouter()
logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="eco-worker")


class EconomicsRequest(BaseModel):
    region_id: str = Field(default="delhi")
    days: int = Field(default=180, ge=30, le=365)
    interventions: List[str] = Field(
        default=["no_action", "partial_lockdown", "full_lockdown",
                 "vaccination_rollout", "combined_strategy"]
    )

    @field_validator("region_id")
    @classmethod
    def val_region(cls, v):
        if v not in DataIngestionService.REGIONS:
            raise ValueError(f"Unknown region: {v}")
        return v

    @field_validator("interventions")
    @classmethod
    def val_iv(cls, v):
        bad = [x for x in v if x not in SEIRModel.VALID_INTERVENTIONS]
        if bad:
            raise ValueError(f"Invalid interventions: {bad}")
        return v


def _run_economics_sync(region_id, days, interventions):
    from services.realtime_service import get_realtime_service
    ds = DataIngestionService()
    rt = get_realtime_service()

    region  = ds.get_region(region_id)
    weather = rt.get_live_weather(region_id)
    disease = rt.get_live_disease_stats(region_id)
    param_dict = ds.get_seir_parameters(region, disease, weather)

    scenario_comps = []
    timelines = {}

    for iv in interventions:
        params = SEIRParameters(**param_dict)
        params = SEIRModel.apply_intervention(params, iv)
        result = SEIRModel(params).run(days=days)
        result.scenario_name = iv
        rd = result.to_dict()
        baseline_inf = 1  # will be set below

        scenario_comps.append({
            "scenario":      iv,
            "total_infected": rd["total_infected"],
            "total_deceased": rd["total_deceased"],
            "peak_infected":  rd["peak_infected"],
            "peak_day":       rd["peak_day"],
        })
        timelines[iv] = rd["timeline"]

    # Set baseline deaths for comparison
    baseline = next((s for s in scenario_comps if s["scenario"] == "no_action"),
                    scenario_comps[0])
    for s in scenario_comps:
        s["lives_saved"] = max(0, baseline["total_deceased"] - s["total_deceased"])

    return {
        "region": region,
        "weather": weather,
        "disease": disease,
        "scenario_comparisons": scenario_comps,
        "timelines": timelines,
    }


@router.post("/analyze")
async def economic_analysis(request: EconomicsRequest):
    """Full cost-benefit and resource allocation analysis across scenarios."""
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            _executor, _run_economics_sync,
            request.region_id, request.days, request.interventions
        )

        eco = get_economic_model()
        analysis = eco.compute_full_analysis(
            region_id=request.region_id,
            population=data["region"]["population"],
            scenario_comparisons=data["scenario_comparisons"],
            simulation_days=request.days,
        )

        # Resource timeline for the no_action (worst case) scenario
        baseline_timeline = data["timelines"].get("no_action",
                            list(data["timelines"].values())[0])
        resource_timeline = eco.compute_resource_timeline(
            timeline=baseline_timeline,
            population=data["region"]["population"],
            region_id=request.region_id,
        )

        return {
            "success": True,
            "region": {"id": data["region"]["id"], "name": data["region"]["name"],
                       "population": data["region"]["population"]},
            "economic_analysis": analysis,
            "resource_timeline": resource_timeline,
            "data_sources": {
                "weather": data["weather"]["source"],
                "disease": data["disease"]["source"],
            }
        }
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Economic analysis error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{region_id}")
async def economics_summary(region_id: str, days: int = 90):
    """Quick economic summary for a region with default interventions."""
    req = EconomicsRequest(region_id=region_id, days=days)
    return await economic_analysis(req)
