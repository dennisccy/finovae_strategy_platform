"""FastAPI router for directions cache endpoints.

Three endpoints:
  GET  /api/directions/cache           — check cache + list summaries
  GET  /api/directions/cache/{id}      — fetch full node for one direction
  POST /api/directions/cache           — save one direction result to cache
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.directions_cache import (
    build_cache_key,
    has_cache,
    list_cached_directions,
    read_direction_full,
    write_direction_result,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Directions Cache"])


class SaveDirectionRequest(BaseModel):
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    exchange: str
    allow_short: bool = False
    leverage: int = 1
    index: int
    direction_id: str
    node: dict


@router.get("/api/directions/cache")
async def get_directions_cache(
    symbol: str = Query(...),
    timeframe: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    exchange: str = Query(...),
    allow_short: bool = Query(False),
    leverage: int = Query(1),
):
    """Check cache and return direction summaries if cached."""
    cache_key = build_cache_key(
        symbol, timeframe, start_date, end_date, exchange, allow_short, leverage
    )
    if not has_cache(cache_key):
        return {"cached": False, "directions": []}
    directions = list_cached_directions(cache_key)
    return {"cached": len(directions) > 0, "directions": directions}


@router.get("/api/directions/cache/{direction_id}")
async def get_cached_direction(
    direction_id: str,
    symbol: str = Query(...),
    timeframe: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    exchange: str = Query(...),
    allow_short: bool = Query(False),
    leverage: int = Query(1),
):
    """Fetch full iteration node for one cached direction."""
    cache_key = build_cache_key(
        symbol, timeframe, start_date, end_date, exchange, allow_short, leverage
    )
    node = read_direction_full(cache_key, direction_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Direction '{direction_id}' not in cache")
    return node


@router.post("/api/directions/cache")
async def save_direction_result(request: SaveDirectionRequest):
    """Save one direction result to the cache."""
    try:
        cache_key = build_cache_key(
            request.symbol,
            request.timeframe,
            request.start_date,
            request.end_date,
            request.exchange,
            request.allow_short,
            request.leverage,
        )
        write_direction_result(cache_key, request.index, request.direction_id, request.node)
        return {"success": True}
    except Exception as e:
        logger.error("Failed to save direction result: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
