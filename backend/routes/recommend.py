"""Policy Recommendation Routes"""
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
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="recommend-worker")


class RecommendRequest(BaseModel):
    region_id: str = Field(default="delhi")
    days: int = Field(default=180, ge=30, le=365)

    @field_validator("region_id")
    @classmethod
    def validate_region_id(cls, v: str) -> str:
        valid = set(DataIngestionService.REGIONS.keys())
        if v.lower().strip() not in valid:
            raise ValueError(f"Unknown region '{v}'. Available: {sorted(valid)}")
        return v.lower().strip()


def _run_recommend_sync(region_id: str, days: int) -> dict:
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
async def get_recommendations(request: RecommendRequest):
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            _executor, _run_recommend_sync, request.region_id, request.days
        )

        orchestrator = AgentOrchestrator()
        agent_data = {
            "region": data["region"],
            "simulation_result": data["sim"],
            "weather_data": data["weather"],
            "disease_stats": data["disease_stats"],
        }

        prediction_result = await orchestrator.prediction_agent.analyze(agent_data)
        risk_result = await orchestrator.risk_agent.analyze(agent_data)

        enriched = {
            **agent_data,
            "prediction_output": prediction_result.output,
            "risk_output": risk_result.output,
        }
        policy_result = await orchestrator.policy_agent.analyze(enriched)

        return {
            "success": True,
            "region": {"id": data["region"]["id"], "name": data["region"]["name"]},
            "recommendations": policy_result.output,
            "reasoning": policy_result.reasoning,
            "confidence": policy_result.confidence,
            "supporting_data": {
                "severity": prediction_result.output.get("severity_level"),
                "r0": prediction_result.output.get("r0"),
                "high_risk_zones": risk_result.output.get("high_risk_count", 0),
            },
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Recommendation error")
        raise HTTPException(status_code=500, detail=str(e))
