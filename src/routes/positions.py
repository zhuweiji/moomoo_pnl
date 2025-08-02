"""API routes for getting position information."""

from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.core.orders.models import CurrentPosition
from src.core.moomoo_client import MoomooClient
from src.routes.utils import get_current_username

router = APIRouter()


@router.get("/current", response_model=List[CurrentPosition])
async def get_current_positions(username: str = Depends(get_current_username)):
    """Get current positions."""
    positions = MoomooClient.get_current_positions()
    if positions is None:
        raise HTTPException(status_code=500, detail="No positions on local Moomoo API")
    return [asdict(p) for p in positions]
