"""Adaptive Learning Routes — agents learn from simulation history."""
import logging
from fastapi import APIRouter, HTTPException

from services.adaptive_service import get_adaptive_service
from services.data_service import DataIngestionService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/insights/{region_id}")
async def regional_insights(region_id: str):
    """Get AI-learned insights from past simulation history."""
    if region_id not in DataIngestionService.REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region_id}")
    try:
        svc = get_adaptive_service()
        insights = await svc.get_regional_insights(region_id)
        return {"region_id": region_id, **insights}
    except Exception as e:
        logger.exception("Insights error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy-rankings/{region_id}")
async def learned_policy_rankings(region_id: str):
    """Return intervention rankings learned from simulation history + RAG."""
    if region_id not in DataIngestionService.REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region_id}")
    try:
        svc = get_adaptive_service()
        rankings = await svc.get_learned_policy_rankings(region_id)
        return {"region_id": region_id, "rankings": rankings}
    except Exception as e:
        logger.exception("Policy rankings error")
        raise HTTPException(status_code=500, detail=str(e))
