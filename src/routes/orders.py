"""API routes for managing trailing stop orders."""

from dataclasses import asdict
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from src.core.orders.managers import OrderManager
from src.core.orders.models import (
    CustomOrderStatus,
    CustomTrailingStopBuyOrder,
    CustomTrailingStopSellOrder,
)

router = APIRouter()
order_manager = OrderManager()
order_manager.start()


class TrailingStopSellOrderCreate(BaseModel):
    """Request model for creating a trailing stop sell order."""

    stock_code: str = Field(..., description="Stock code to create order for")
    min_price: float = Field(..., gt=0, description="Minimum price threshold")
    quantity: int = Field(..., gt=0, description="Number of shares to sell")
    trailing_amount: Optional[float] = Field(
        None, gt=0, description="Fixed amount to trail by"
    )
    trailing_percent: Optional[float] = Field(
        None, gt=0, lt=100, description="Percentage to trail by"
    )

    @model_validator(mode="after")
    def validate_trailing_options(cls, model_instance):
        """Ensure only one of trailing_amount or trailing_percent is specified."""
        if (
            model_instance.trailing_amount is not None
            and model_instance.trailing_percent is not None
        ):
            raise ValueError("Cannot specify both trailing_amount and trailing_percent")

        if (
            model_instance.trailing_amount is None
            and model_instance.trailing_percent is None
        ):
            raise ValueError("Must specify either trailing_amount or trailing_percent")

        return model_instance


class TrailingStopBuyOrderCreate(BaseModel):
    """Request model for creating a trailing stop buy order."""

    stock_code: str = Field(..., description="Stock code to create order for")
    max_price: float = Field(..., gt=0, description="Maximum price threshold")
    quantity: int = Field(..., gt=0, description="Number of shares to buy")
    trailing_amount: Optional[float] = Field(
        None, gt=0, description="Fixed amount to trail by"
    )
    trailing_percent: Optional[float] = Field(
        None, gt=0, lt=100, description="Percentage to trail by"
    )

    @model_validator(mode="after")
    def validate_trailing_options(cls, model_instance):
        """Ensure only one of trailing_amount or trailing_percent is specified."""
        if (
            model_instance.trailing_amount is not None
            and model_instance.trailing_percent is not None
        ):
            raise ValueError("Cannot specify both trailing_amount and trailing_percent")

        if (
            model_instance.trailing_amount is None
            and model_instance.trailing_percent is None
        ):
            raise ValueError("Must specify either trailing_amount or trailing_percent")

        return model_instance


class TrailingStopSellOrderUpdate(BaseModel):
    """Request model for updating a trailing stop sell order."""

    min_price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    trailing_amount: Optional[float] = Field(None, gt=0)
    trailing_percent: Optional[float] = Field(None, gt=0, lt=100)

    @model_validator(mode="after")
    def validate_trailing_options(cls, model_instance):
        """Ensure only one of trailing_amount or trailing_percent is specified."""
        if (
            model_instance.trailing_amount is not None
            and model_instance.trailing_percent is not None
        ):
            raise ValueError("Cannot specify both trailing_amount and trailing_percent")

        return model_instance


class TrailingStopBuyOrderUpdate(BaseModel):
    """Request model for updating a trailing stop buy order."""

    max_price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    trailing_amount: Optional[float] = Field(None, gt=0)
    trailing_percent: Optional[float] = Field(None, gt=0, lt=100)

    @model_validator(mode="after")
    def validate_trailing_options(cls, model_instance):
        """Ensure only one of trailing_amount or trailing_percent is specified."""
        if (
            model_instance.trailing_amount is not None
            and model_instance.trailing_percent is not None
        ):
            raise ValueError("Cannot specify both trailing_amount and trailing_percent")

        return model_instance


@router.post("/sell_orders", response_model=CustomTrailingStopSellOrder)
async def create_sell_order(order: TrailingStopSellOrderCreate):
    """Create a new trailing stop sell order."""
    try:
        new_order = CustomTrailingStopSellOrder.create(
            stock_code=order.stock_code,
            min_price=order.min_price,
            quantity=order.quantity,
            trailing_amount=order.trailing_amount,
            trailing_percent=order.trailing_percent,
        )
        order_manager.add_order(new_order)
        return new_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/buy_orders", response_model=CustomTrailingStopBuyOrder)
async def create_buy_order(order: TrailingStopBuyOrderCreate):
    """Create a new trailing stop buy order."""
    try:
        new_order = CustomTrailingStopBuyOrder.create(
            stock_code=order.stock_code,
            max_price=order.max_price,
            quantity=order.quantity,
            trailing_amount=order.trailing_amount,
            trailing_percent=order.trailing_percent,
        )
        order_manager.add_order(new_order)
        return new_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sell_orders")
async def list_sell_orders(status: Optional[CustomOrderStatus] = None):
    """List all trailing stop sell orders, optionally filtered by status."""
    orders = order_manager.get_all_orders()
    orders = [
        order for order in orders if isinstance(order, CustomTrailingStopSellOrder)
    ]

    if status:
        orders = [order for order in orders if order.status == status]

    response_data = []
    for order in orders:
        order_as_json = asdict(order)
        order_as_json["trigger_price"] = order.get_trigger_price()
        response_data.append(order_as_json)

    return response_data


@router.get("/buy_orders")
async def list_buy_orders(status: Optional[CustomOrderStatus] = None):
    """List all trailing stop buy orders, optionally filtered by status."""
    orders = order_manager.get_all_orders()
    orders = [
        order for order in orders if isinstance(order, CustomTrailingStopBuyOrder)
    ]
    if status:
        orders = [order for order in orders if order.status == status]

    response_data = []
    for order in orders:
        order_as_json = asdict(order)
        order_as_json["trigger_price"] = order.get_trigger_price()
        response_data.append(order_as_json)

    return response_data


@router.get("/sell_orders/{order_id}", response_model=CustomTrailingStopSellOrder)
async def get_sell_order(order_id: str):
    """Get a specific trailing stop sell order by ID."""
    order = order_manager.get_order(order_id)
    if not order or not isinstance(order, CustomTrailingStopSellOrder):
        raise HTTPException(status_code=404, detail="Sell order not found")
    return order


@router.get("/buy_orders/{order_id}", response_model=CustomTrailingStopBuyOrder)
async def get_buy_order(order_id: str):
    """Get a specific trailing stop buy order by ID."""
    order = order_manager.get_order(order_id)
    if not order or not isinstance(order, CustomTrailingStopBuyOrder):
        raise HTTPException(status_code=404, detail="Buy order not found")
    return order


@router.patch("/sell_orders/{order_id}", response_model=CustomTrailingStopSellOrder)
async def update_sell_order(order_id: str, update_data: TrailingStopSellOrderUpdate):
    """Update a trailing stop sell order."""
    order = order_manager.get_order(order_id)
    if not order or not isinstance(order, CustomTrailingStopSellOrder):
        raise HTTPException(status_code=404, detail="Sell order not found")

    if order.status != CustomOrderStatus.WAITING:
        raise HTTPException(
            status_code=400, detail=f"Cannot update order in status {order.status}"
        )

    try:
        # Update fields if provided
        if update_data.min_price is not None:
            order.min_price = update_data.min_price
        if update_data.quantity is not None:
            order.quantity = update_data.quantity
        if update_data.trailing_amount is not None:
            order.trailing_amount = update_data.trailing_amount
            order.trailing_percent = None
        if update_data.trailing_percent is not None:
            order.trailing_percent = update_data.trailing_percent
            order.trailing_amount = None

        order_manager._save_orders()
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/buy_orders/{order_id}", response_model=CustomTrailingStopBuyOrder)
async def update_buy_order(order_id: str, update_data: TrailingStopBuyOrderUpdate):
    """Update a trailing stop buy order."""
    order = order_manager.get_order(order_id)
    if not order or not isinstance(order, CustomTrailingStopBuyOrder):
        raise HTTPException(status_code=404, detail="Buy order not found")

    if order.status != CustomOrderStatus.WAITING:
        raise HTTPException(
            status_code=400, detail=f"Cannot update order in status {order.status}"
        )

    try:
        # Update fields if provided
        if update_data.max_price is not None:
            order.max_price = update_data.max_price
        if update_data.quantity is not None:
            order.quantity = update_data.quantity
        if update_data.trailing_amount is not None:
            order.trailing_amount = update_data.trailing_amount
            order.trailing_percent = None
        if update_data.trailing_percent is not None:
            order.trailing_percent = update_data.trailing_percent
            order.trailing_amount = None

        order_manager._save_orders()
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sell_orders/{order_id}", status_code=204)
async def delete_sell_order(order_id: str):
    """Cancel a trailing stop sell order."""
    try:
        order = order_manager.get_order(order_id)
        if not order or not isinstance(order, CustomTrailingStopSellOrder):
            raise HTTPException(status_code=404, detail="Sell order not found")
        order_manager.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/buy_orders/{order_id}", status_code=204)
async def delete_buy_order(order_id: str):
    """Cancel a trailing stop buy order."""
    try:
        order = order_manager.get_order(order_id)
        if not order or not isinstance(order, CustomTrailingStopBuyOrder):
            raise HTTPException(status_code=404, detail="Buy order not found")
        order_manager.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
