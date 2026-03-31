"""Regions Routes"""
import logging
from fastapi import APIRouter, HTTPException
from services.data_service import DataIngestionService

router = APIRouter()
logger = logging.getLogger(__name__)
data_service = DataIngestionService()


@router.get("")
async def get_all_regions():
    return {"regions": data_service.get_all_regions()}


@router.get("/{region_id}")
async def get_region(region_id: str):
    try:
        region = data_service.get_region(region_id)
        weather = data_service.get_weather_data(region)
        disease_stats = data_service.get_current_disease_stats(region)
        historical = data_service.get_historical_disease_data(region_id)
        return {
            "region": region,
            "weather": weather,
            "disease_stats": disease_stats,
            "historical_data": historical[-30:],
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{region_id}/historical")
async def get_historical_data(region_id: str):
    try:
        data = data_service.get_historical_disease_data(region_id)
        return {"region_id": region_id, "historical_data": data}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
