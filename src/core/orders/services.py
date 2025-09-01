import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from moomoo import RET_OK, TrdSide
from moomoo.common.constant import OrderType, TimeInForce, TrdEnv

from src.core.external_data_services.stock_data.yfinance import get_stock_price
from src.core.moomoo_client import MoomooClient
from src.core.orders.models import (
    CustomOrderStatus,
    PriceBucketModel,
    RangeBucketBuyOrderModel,
    TrailingStopBuyOrderModel,
    TrailingStopSellOrderModel,
)
from src.core.orders.repositories import (
    BaseCustomOrderRepository,
    RangeBucketBuyOrderRepository,
    TrailingStopBuyOrderRepository,
    TrailingStopSellOrderRepository,
)
from src.core.utilities import get_logger

log = get_logger(__name__)


class OrderService(ABC):
    """Base class for order services."""

    def __init__(self, is_simulated_env: bool = False):
        self.is_simulated_env = is_simulated_env
        if "PYTEST_CURRENT_TEST" in os.environ and not is_simulated_env:
            raise ValueError("About to run a non-simulated trade in a test environment. Are you sure?")

        self.repository: type[BaseCustomOrderRepository] = None  # type: ignore

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


class RangeBucketBuyOrderService(OrderService):
    """Service for operations on range bucket orders"""

    def __init__(self, is_simulated_env: bool = False):
        super().__init__(is_simulated_env)
        self.repository = RangeBucketBuyOrderRepository

    def validate_new_order(self, order: RangeBucketBuyOrderModel, positions) -> None:
        """Validate a new order can be placed."""
        if order.quantity <= 0:
            raise ValueError("Order quantity must be greater than 0")

        if not order.buckets or len(order.buckets) == 0:
            raise ValueError("Range bucket order must have at least one bucket")

        # Check that buckets have valid prices
        for bucket in order.buckets:
            if bucket.price <= 0:
                raise ValueError(f"Bucket price must be greater than 0, got {bucket.price}")

    def can_cancel_order(self, order: RangeBucketBuyOrderModel) -> bool:
        """Check if an order can be cancelled."""
        return order.status == CustomOrderStatus.WAITING.value

    def is_order_waiting(self, order: RangeBucketBuyOrderModel) -> bool:
        """Check if an order is in waiting status."""
        return order.status == CustomOrderStatus.WAITING.value

    def get_current_price(self, order: RangeBucketBuyOrderModel, positions):
        """Get current price for the stock."""
        # First try to get from positions
        matching_positions = [i for i in positions if i.code == order.stock_code]
        if matching_positions:
            return matching_positions[0].nominal_price

        return get_stock_price(order.stock_code)

    def execute_order(self, order: RangeBucketBuyOrderModel) -> None:
        """Execute a single bucket buy order."""
        trading_env = TrdEnv.SIMULATE if self.is_simulated_env else TrdEnv.REAL

        # Find the first non-triggered bucket
        bucket_to_execute = next((b for b in order.buckets if not b.is_triggered), None)
        if not bucket_to_execute:
            log.info(f"No remaining buckets to execute for order {order.id}")
            order.status = CustomOrderStatus.COMPLETED.value
            self.repository.update(order, self.repository.get_db_session())
            return

        try:
            bucket_price = bucket_to_execute.price
            qty = self.get_bucket_quantity(order, bucket_price)

            with MoomooClient.get_trade_context() as trd_ctx:
                ret, data = trd_ctx.unlock_trade(os.getenv("MOOMOO_TRADING_PASSWORD"))
                if ret == RET_OK:
                    log.info("unlock success!")
                else:
                    log.info("unlock_trade failed: ", data)

                ret, data = trd_ctx.place_order(
                    price=bucket_price,  # Limit order at bucket price
                    qty=qty,
                    code=order.stock_code,
                    trd_side=TrdSide.BUY,
                    order_type=OrderType.NORMAL,
                    adjust_limit=0,
                    trd_env=trading_env,
                    time_in_force=TimeInForce.DAY,
                    remark=f"Range bucket buy order {order.id}",
                )

                if ret != RET_OK:
                    raise Exception(f"Failed to place order: {data}")

            # Mark this bucket as triggered
            self.mark_bucket_triggered(order, bucket_price)
            log.info(f"Successfully executed bucket buy at ${bucket_price:.2f} for order {order.id}")
            self.repository.update(order, self.repository.get_db_session())

        except Exception as e:
            self.set_error_status(order, str(e))
            log.error(f"Error executing order {order.id}: {e}")
            raise

    def set_error_status(self, order: RangeBucketBuyOrderModel, error_msg: str) -> None:
        """Set order status to error with message."""
        order.status = CustomOrderStatus.ERROR.value
        order.error_message = error_msg
        order.updated_on = datetime.now()

        # Add repository update
        self.repository.update(order, self.repository.get_db_session())

    def mark_bucket_triggered(self, order: RangeBucketBuyOrderModel, price: float) -> None:
        """Mark a bucket price as triggered (after placing order)."""
        for bucket in order.buckets:
            if abs(bucket.price - price) <= order.price_tolerance and not bucket.is_triggered:
                bucket.is_triggered = True
                bucket.trigger_time = datetime.now()

                # Check if all buckets are triggered
                if all(b.is_triggered for b in order.buckets):
                    order.status = CustomOrderStatus.COMPLETED.value
                break

    @staticmethod
    def get_remaining_buckets(order: RangeBucketBuyOrderModel) -> list[PriceBucketModel]:
        """Get list of remaining bucket objects not yet triggered."""
        return [bucket for bucket in order.buckets if not bucket.is_triggered]

    @staticmethod
    def get_bucket_quantity(order: RangeBucketBuyOrderModel, bucket_price: float) -> int:
        """Calculate the quantity to buy at a specific bucket price."""
        matching_bucket = None
        for bucket in order.buckets:
            if abs(bucket.price - bucket_price) <= order.price_tolerance:
                matching_bucket = bucket
                break

        if not matching_bucket:
            raise ValueError(f"Price {bucket_price} is not in the bucket list")

        # Default to equal distribution across all buckets
        bucket_count = len(order.buckets)
        if bucket_count <= 0:
            return 0

        base_quantity = order.quantity // bucket_count
        remainder = order.quantity % bucket_count

        # Distribute remainder to lower price buckets (better value)
        bucket_index = order.buckets.index(matching_bucket)
        if bucket_index < remainder:
            return base_quantity + 1

        return base_quantity

    @staticmethod
    def get_bucket_summary(order: RangeBucketBuyOrderModel) -> str:
        """Return a text representation of buckets and their status."""
        result = []
        for bucket in order.buckets:
            status = "✓" if bucket.is_triggered else "○"
            qty = RangeBucketBuyOrderService.get_bucket_quantity(order, bucket.price)
            result.append(f"{status} ${bucket.price:.2f} ({qty} shares)")

        return "\n".join(result)


class TrailingStopSellOrderService(OrderService):
    """Service for handling trailing stop sell orders."""

    def __init__(self, is_simulated_env: bool = False):
        super().__init__(is_simulated_env)
        self.repository = TrailingStopSellOrderRepository

    def validate_new_order(self, order: TrailingStopSellOrderModel, positions) -> None:
        position = [i for i in positions if i.code == order.stock_code]
        if not position:
            raise ValueError(f"Unable to find matching position for sell order: {order.stock_code}")

        matching_position = position[0]
        if matching_position.can_sell_qty < order.quantity:
            raise ValueError(f"Insufficient shares. Own: {matching_position.can_sell_qty}, Required: {order.quantity}")

    def can_cancel_order(self, order: TrailingStopSellOrderModel) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def is_order_waiting(self, order: TrailingStopSellOrderModel) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def get_current_price(self, order: TrailingStopSellOrderModel, positions):
        matching_positions = [i for i in positions if i.code == order.stock_code]
        if not matching_positions:
            raise ValueError("Cannot get data about a stock that hasn't already been bought")
        return matching_positions[0].nominal_price

    def execute_order(self, order: TrailingStopSellOrderModel) -> None:
        trading_env = TrdEnv.SIMULATE if self.is_simulated_env else TrdEnv.REAL

        try:
            order.status = CustomOrderStatus.TRIGGERED
            order.updated_on = datetime.now(tz=timezone.utc)
            self.repository.update(order, self.repository.get_db_session())

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
                    trd_env=trading_env,
                    time_in_force=TimeInForce.DAY,
                    remark=f"Trailing stop sell order {order.id}",
                )

                if ret != RET_OK:
                    raise Exception(f"Failed to place order: {data}")

            order.status = CustomOrderStatus.COMPLETED
            log.info(f"Successfully executed sell order {order.id}")
            self.repository.update(order, self.repository.get_db_session())

        except Exception as e:
            self.set_error_status(order, str(e))
            raise

    def set_error_status(self, order: TrailingStopSellOrderModel, error_msg: str) -> None:
        order.status = CustomOrderStatus.ERROR
        order.error_message = error_msg
        order.updated_on = datetime.now()
        self.repository.update(order, self.repository.get_db_session())


class TrailingStopBuyOrderService(OrderService):
    """Service for handling trailing stop buy orders."""

    def __init__(self, is_simulated_env: bool = False):
        super().__init__(is_simulated_env)
        self.repository = TrailingStopBuyOrderRepository

    def validate_new_order(self, order: TrailingStopBuyOrderModel, positions) -> None:
        # No validation needed for buy orders as we don't need existing position
        pass

    def can_cancel_order(self, order: TrailingStopBuyOrderModel) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def is_order_waiting(self, order: TrailingStopBuyOrderModel) -> bool:
        return order.status == CustomOrderStatus.WAITING

    def get_current_price(self, order: TrailingStopBuyOrderModel, positions):
        """Get current price for the stock using yfinance.

        For stocks in current positions, use position data.
        For custom stocks, fetch from yfinance.
        """
        # First try to get from positions
        matching_positions = [i for i in positions if i.code == order.stock_code]
        if matching_positions:
            return matching_positions[0].nominal_price

        return get_stock_price(order.stock_code)

    def execute_order(self, order: TrailingStopBuyOrderModel) -> None:
        trading_env = TrdEnv.SIMULATE if self.is_simulated_env else TrdEnv.REAL

        try:
            order.status = CustomOrderStatus.TRIGGERED
            order.updated_on = datetime.now()
            self.repository.update(order, self.repository.get_db_session())

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
                    trd_env=trading_env,
                    time_in_force=TimeInForce.DAY,
                    remark=f"Trailing stop buy order {order.id}",
                )

                if ret != RET_OK:
                    raise Exception(f"Failed to place order: {data}")

            order.status = CustomOrderStatus.COMPLETED
            log.info(f"Successfully executed buy order {order.id}")
            self.repository.update(order, self.repository.get_db_session())

        except Exception as e:
            self.set_error_status(order, str(e))
            raise

    def set_error_status(self, order: TrailingStopBuyOrderModel, error_msg: str) -> None:
        order.status = CustomOrderStatus.ERROR
        order.error_message = error_msg
        order.updated_on = datetime.now()
        self.repository.update(order, self.repository.get_db_session())
