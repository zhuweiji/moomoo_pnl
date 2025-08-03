"""Services for handling different types of orders."""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

from moomoo import RET_OK, TrdSide
from moomoo.common.constant import OrderType, TimeInForce, TrdEnv

from src.core.external_data_services.stock_data.yfinance import get_stock_price
from src.core.moomoo_client import MoomooClient
from src.core.orders.models import (
    CustomOrderStatus,
    CustomTrailingStopBuyOrder,
    CustomTrailingStopSellOrder,
)
from src.core.utilities import get_logger

log = get_logger(__name__)


class OrderService(ABC):
    """Base class for order services."""

    def __init__(self, is_simulated_env: bool = False):
        self.is_simulated_env = is_simulated_env

    @abstractmethod
    def validate_new_order(self, order, positions) -> None:
        """Validate a new order can be placed."""
        pass

    @abstractmethod
    def can_cancel_order(self, order) -> bool:
        """Check if an order can be cancelled."""
        pass

    @abstractmethod
    def is_order_waiting(self, order) -> bool:
        """Check if an order is in waiting status."""
        pass

    @abstractmethod
    def get_current_price(self, order, positions):
        """Get current price for the order's stock."""
        pass

    @abstractmethod
    def execute_order(self, order) -> None:
        """Execute the order."""
        pass

    @abstractmethod
    def set_error_status(self, order, error_msg: str) -> None:
        """Set order status to error with message."""
        pass


class TrailingStopSellOrderService(OrderService):
    """Service for handling trailing stop sell orders."""

    def validate_new_order(self, order: CustomTrailingStopSellOrder, positions) -> None:
        position = [i for i in positions if i.code == order.stock_code]
        if not position:
            raise ValueError(f"Unable to find matching position for sell order: {order.stock_code}")

        matching_position = position[0]
        if matching_position.can_sell_qty < order.quantity:
            raise ValueError(f"Insufficient shares. Own: {matching_position.can_sell_qty}, Required: {order.quantity}")

    def can_cancel_order(self, order: CustomTrailingStopSellOrder) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def is_order_waiting(self, order: CustomTrailingStopSellOrder) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def get_current_price(self, order: CustomTrailingStopSellOrder, positions):
        matching_positions = [i for i in positions if i.code == order.stock_code]
        if not matching_positions:
            raise ValueError("Cannot get data about a stock that hasn't already been bought")
        return matching_positions[0].nominal_price

    def execute_order(self, order: CustomTrailingStopSellOrder) -> None:
        simulated_trading_env = TrdEnv.SIMULATE if self.is_simulated_env else TrdEnv.REAL

        try:
            order.status = CustomOrderStatus.TRIGGERED
            order.updated_at = datetime.now()

            with MoomooClient.get_trade_context() as trd_ctx:
                ret, data = trd_ctx.unlock_trade(os.getenv("MOOMOO_TRADING_PASSWORD"))
                if ret == RET_OK:
                    log.info("unlock success!")
                else:
                    log.info("unlock_trade failed: ", data)

                ret, data = trd_ctx.place_order(
                    price=0.0,  # Market order
                    qty=order.quantity,
                    code=order.stock_code,
                    trd_side=TrdSide.SELL,
                    order_type=OrderType.MARKET,
                    adjust_limit=0,
                    trd_env=simulated_trading_env,
                    time_in_force=TimeInForce.DAY,
                    remark=f"Trailing stop sell order {order.id}",
                )

                if ret != RET_OK:
                    raise Exception(f"Failed to place order: {data}")

            order.status = CustomOrderStatus.COMPLETED
            log.info(f"Successfully executed sell order {order.id}")

        except Exception as e:
            self.set_error_status(order, str(e))
            raise

    def set_error_status(self, order: CustomTrailingStopSellOrder, error_msg: str) -> None:
        order.status = CustomOrderStatus.ERROR
        order.error_message = error_msg
        order.updated_at = datetime.now()


class TrailingStopBuyOrderService(OrderService):
    """Service for handling trailing stop buy orders."""

    def validate_new_order(self, order: CustomTrailingStopBuyOrder, positions) -> None:
        # No validation needed for buy orders as we don't need existing position
        pass

    def can_cancel_order(self, order: CustomTrailingStopBuyOrder) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def is_order_waiting(self, order: CustomTrailingStopBuyOrder) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def get_current_price(self, order: CustomTrailingStopBuyOrder, positions):
        """Get current price for the stock using yfinance.

        For stocks in current positions, use position data.
        For custom stocks, fetch from yfinance.
        """
        # First try to get from positions
        matching_positions = [i for i in positions if i.code == order.stock_code]
        if matching_positions:
            return matching_positions[0].nominal_price

        return get_stock_price(order.stock_code)

    def execute_order(self, order: CustomTrailingStopBuyOrder) -> None:
        simulated_trading_env = TrdEnv.SIMULATE if self.is_simulated_env else TrdEnv.REAL

        try:
            order.status = CustomOrderStatus.TRIGGERED
            order.updated_at = datetime.now()

            with MoomooClient.get_trade_context() as trd_ctx:
                ret, data = trd_ctx.unlock_trade(os.getenv("MOOMOO_TRADING_PASSWORD"))
                if ret == RET_OK:
                    log.info("unlock success!")
                else:
                    log.info("unlock_trade failed: ", data)

                ret, data = trd_ctx.place_order(
                    price=0.0,  # Market order
                    qty=order.quantity,
                    code=order.stock_code,
                    trd_side=TrdSide.BUY,
                    order_type=OrderType.MARKET,
                    adjust_limit=0,
                    trd_env=simulated_trading_env,
                    time_in_force=TimeInForce.DAY,
                    remark=f"Trailing stop buy order {order.id}",
                )

                if ret != RET_OK:
                    raise Exception(f"Failed to place order: {data}")

            order.status = CustomOrderStatus.COMPLETED
            log.info(f"Successfully executed buy order {order.id}")

        except Exception as e:
            self.set_error_status(order, str(e))
            raise

    def set_error_status(self, order: CustomTrailingStopBuyOrder, error_msg: str) -> None:
        order.status = CustomOrderStatus.ERROR
        order.error_message = error_msg
        order.updated_at = datetime.now()
