"""Real-Time Data Routes — live feeds from external APIs."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from services.realtime_service import get_realtime_service
from services.data_service import DataIngestionService

router = APIRouter()
logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rt-worker")


@router.get("/{region_id}")
async def get_realtime_data(region_id: str):
    """Fetch all live data for a region: weather, disease, AQI, mobility."""
    if region_id not in DataIngestionService.REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region_id}")
    try:
        loop = asyncio.get_running_loop()
        svc = get_realtime_service()
        data = await loop.run_in_executor(_executor, svc.get_all_realtime, region_id)
        return {"success": True, "region_id": region_id, **data}
    except Exception as e:
        logger.exception("Realtime data error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{region_id}/weather")
async def get_live_weather(region_id: str):
    if region_id not in DataIngestionService.REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region_id}")
    svc = get_realtime_service()
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(_executor, svc.get_live_weather, region_id)
    return data


@router.get("/{region_id}/disease")
async def get_live_disease(region_id: str):
    if region_id not in DataIngestionService.REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region_id}")
    svc = get_realtime_service()
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(_executor, svc.get_live_disease_stats, region_id)
    return data
