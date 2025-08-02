"""API routes for managing trailing stop orders."""

from fastapi import APIRouter, HTTPException

from src.core.external_data_services.stock_data.yfinance import get_stock_price

router = APIRouter()


@router.get("/stock-price/{stock_code}")
async def get_stock_price_endpoint(stock_code: str):
    try:
        return {"price": get_stock_price(stock_code)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
