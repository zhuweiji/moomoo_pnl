import os
from abc import ABC, abstractmethod
from datetime import datetime

from moomoo import RET_OK, TrdSide
from moomoo.common.constant import OrderType, TimeInForce, TrdEnv

from src.core.orders.models2 import (
    CustomOrderStatus,
    PriceBucket,
    RangeBucketBuyOrderModel,
)
from src.core.orders.repositories2 import RangeBucketBuyOrderRepository
from src.core.orders.services import MoomooClient, OrderService, TrdEnv, get_stock_price
from src.core.utilities import get_logger

log = get_logger(__name__)


class RangeBucketBuyOrderService(OrderService):
    """Service for operations on range bucket orders"""

    def __init__(self, is_simulated_env: bool = False):
        super().__init__(is_simulated_env)
        self.repository = RangeBucketBuyOrderRepository()

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
    def get_remaining_buckets(order: RangeBucketBuyOrderModel) -> list[PriceBucket]:
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
