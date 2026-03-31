"""Prediction Routes"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from models.seir_model import SEIRModel, SEIRParameters
from services.data_service import DataIngestionService
from agents.orchestrator import AgentOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)
data_service = DataIngestionService()
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="predict-worker")


class PredictRequest(BaseModel):
    region_id: str = Field(default="delhi")
    days: int = Field(default=90, ge=7, le=365)

    @field_validator("region_id")
    @classmethod
    def validate_region_id(cls, v: str) -> str:
        valid = set(DataIngestionService.REGIONS.keys())
        if v.lower().strip() not in valid:
            raise ValueError(f"Unknown region '{v}'. Available: {sorted(valid)}")
        return v.lower().strip()


def _run_predict_sync(region_id: str, days: int) -> dict:
    region = data_service.get_region(region_id)
    weather = data_service.get_weather_data(region)
    disease_stats = data_service.get_current_disease_stats(region)
    param_dict = data_service.get_seir_parameters(region, disease_stats, weather)
    params = SEIRParameters(**param_dict)
    result = SEIRModel(params).run(days=days)
    return {
        "region": region,
        "weather": weather,
        "disease_stats": disease_stats,
        "sim": result.to_dict(),
    }


@router.post("")
async def predict(request: PredictRequest):
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            _executor, _run_predict_sync, request.region_id, request.days
        )

        orchestrator = AgentOrchestrator()
        agent_data = {
            "region": data["region"],
            "simulation_result": data["sim"],
            "weather_data": data["weather"],
            "disease_stats": data["disease_stats"],
        }
        prediction_result = await orchestrator.prediction_agent.analyze(agent_data)

        return {
            "success": True,
            "region": {"id": data["region"]["id"], "name": data["region"]["name"]},
            "prediction": prediction_result.output,
            "reasoning": prediction_result.reasoning,
            "confidence": prediction_result.confidence,
            "recommendations": prediction_result.recommendations,
            "timeline_summary": data["sim"]["timeline"][::7],
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Prediction error")
        raise HTTPException(status_code=500, detail=str(e))
