"""Data models for the application."""

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Union
from uuid import UUID, uuid4

from src.core.utilities import get_logger

log = get_logger(__name__)


@dataclass
class HistoricalOrder:
    """moomoo data object"""

    code: str
    stock_name: str

    trd_side: str
    order_type: str
    order_status: str
    order_id: str
    qty: float
    price: float
    create_time: str
    updated_time: str
    dealt_qty: float
    dealt_avg_price: float
    last_err_msg: Optional[str]  # Can be empty
    remark: Optional[str]  # Can be empty
    time_in_force: str
    fill_outside_rth: bool
    aux_price: Union[str, float]  # "N/A" or a float
    trail_type: str  # "N/A" or specific values
    trail_value: Union[str, float]  # "N/A" or a float
    trail_spread: Union[str, float]  # "N/A" or a float
    currency: str


@dataclass
class CurrentPosition:
    """moomoo data object"""

    code: str
    stock_name: str
    qty: float
    can_sell_qty: float
    cost_price: float
    cost_price_valid: bool
    market_val: float
    nominal_price: float
    pl_ratio: float
    pl_ratio_valid: bool
    pl_val: float
    pl_val_valid: bool
    today_buy_qty: float
    today_buy_val: float
    today_pl_val: float
    today_trd_val: float
    today_sell_qty: float
    today_sell_val: float
    position_side: str
    unrealized_pl: Union[str, float]  # N/A treated as str, or it could be float if parsed differently
    realized_pl: Union[str, float]  # Same as unrealized_pl
    currency: str


class CustomOrderStatus(Enum):
    """Status of a custom order."""

    WAITING = "waiting"  # Waiting for conditions to be met
    TRIGGERED = "triggered"  # Conditions met, market order being placed
    COMPLETED = "completed"  # Market order executed
    CANCELLED = "cancelled"  # Order was cancelled by user
    ERROR = "error"  # Error occurred during execution


@dataclass(kw_only=True)
class BaseCustomOrder(ABC):
    """Base class for all custom stock orders."""

    # Core order fields
    id: str
    stock_code: str
    quantity: int

    # Status and timing
    status: CustomOrderStatus = CustomOrderStatus.WAITING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Tracking fields
    last_checked_price: Optional[float] = None
    last_check_time: Optional[datetime] = None

    # Error handling and notes
    error_message: Optional[str] = None
    comments: Optional[str] = None

    @classmethod
    def _validate_common_params(
        cls,
        quantity: int,
    ) -> None:
        """Validate common parameters for all order types."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

    @abstractmethod
    def get_trigger_price(self) -> Optional[float]:
        """Calculate the price that would trigger this order."""
        pass

    @abstractmethod
    def should_trigger(self, current_price: float) -> bool:
        """Check if the order should be triggered based on current price."""
        pass


# TODO incorporate this new order - add service and register with the manager
@dataclass(kw_only=True)
class RangeBucketOrder(BaseCustomOrder):
    """
    A custom order that buys across a range of prices divided into buckets.
    Either specify num_buckets or bucket_size, but not both.
    """

    start_price: float
    end_price: float
    num_buckets: Optional[int] = None
    bucket_size: Optional[float] = None

    triggered_buckets: list[float] = field(default_factory=list)
    buckets: list[float] = field(init=False)

    # should add utility properties like total price of order

    def __post_init__(self):
        if self.start_price >= self.end_price:
            raise ValueError("start_price must be less than end_price")

        if self.num_buckets and self.bucket_size:
            raise ValueError("Specify only one: num_buckets or bucket_size")

        if not self.num_buckets and not self.bucket_size:
            raise ValueError("Must specify either num_buckets or bucket_size")

        # Create buckets
        self.buckets = self._generate_buckets()
        # Validate total quantity distribution (could extend here)

    def get_trigger_price(self) -> Optional[float]:
        """
        Return the next untriggered bucket price that should trigger.
        """
        for price in self.buckets:
            if price not in self.triggered_buckets:
                return price
        return None  # All buckets triggered

    def should_trigger(self, current_price: float) -> bool:
        """
        Check if current price matches an untriggered bucket.
        """
        # Use some tolerance because of float precision issues
        tolerance = 1e-4
        for price in self.buckets:
            if price not in self.triggered_buckets:
                if abs(current_price - price) <= tolerance:
                    return True
        return False

    def _generate_buckets(self) -> list[float]:
        """Generate the list of bucket prices."""
        if self.num_buckets:
            step = (self.end_price - self.start_price) / (self.num_buckets - 1)
            return [round(self.start_price + i * step, 4) for i in range(self.num_buckets)]

        else:
            assert self.bucket_size
            num_buckets = math.floor((self.end_price - self.start_price) / self.bucket_size) + 1
            return [
                round(self.start_price + i * self.bucket_size, 4)
                for i in range(num_buckets)
                if self.start_price + i * self.bucket_size <= self.end_price + 1e-8
            ]

    def mark_bucket_triggered(self, price: float):
        """
        Mark a bucket price as triggered (after placing order).
        """
        if price in self.buckets and price not in self.triggered_buckets:
            self.triggered_buckets.append(price)
            self.updated_at = datetime.now()
            if len(self.triggered_buckets) == len(self.buckets):
                self.status = CustomOrderStatus.COMPLETED

    def remaining_buckets(self) -> list[float]:
        """
        Get list of remaining bucket prices not yet triggered.
        """
        return [price for price in self.buckets if price not in self.triggered_buckets]


@dataclass
class CustomTrailingStopSellOrder:
    # todo - this dataclass should inherit from BaseCustomOrder
    """Represents a trailing stop order."""

    id: str
    stock_code: str
    quantity: int

    min_price: float

    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    last_checked_price: Optional[float] = None
    last_check_time: Optional[datetime] = None
    error_message: Optional[str] = None
    comments: Optional[str] = None

    highest_price: float = 0  # tracks the highest price seen
    trailing_amount: Optional[float] = None  # mutually exclusive with trailing_percent
    trailing_percent: Optional[float] = None  # mutually exclusive with trailing_amount
    status: CustomOrderStatus = CustomOrderStatus.WAITING

    @classmethod
    def create(
        cls,
        stock_code: str,
        min_price: float,
        quantity: int,
        trailing_amount: Optional[float] = None,
        trailing_percent: Optional[float] = None,
    ) -> "CustomTrailingStopSellOrder":
        """Create a new trailing stop order with validation."""
        if trailing_amount is not None and trailing_percent is not None:
            raise ValueError("Cannot specify both trailing_amount and trailing_percent")
        if trailing_amount is None and trailing_percent is None:
            raise ValueError("Must specify either trailing_amount or trailing_percent")
        if trailing_amount is not None and trailing_amount <= 0:
            raise ValueError("Trailing amount must be positive")
        if trailing_percent is not None and (trailing_percent <= 0 or trailing_percent >= 100):
            raise ValueError("Trailing percent must be between 0 and 100")
        if min_price <= 0:
            raise ValueError("Minimum price must be positive")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        return cls(
            id=str(uuid4()),
            stock_code=stock_code,
            min_price=min_price,
            quantity=quantity,
            trailing_amount=trailing_amount,
            trailing_percent=trailing_percent,
        )

    def get_trigger_price(self) -> Optional[float]:
        """Calculate the price that would trigger this order."""
        if self.highest_price == 0:
            return None

        if self.trailing_amount is not None:
            return self.highest_price - self.trailing_amount
        elif self.trailing_percent is not None:
            return self.highest_price * (1 - self.trailing_percent / 100)
        return None

    def should_trigger(self, current_price: float) -> bool:
        """Check if the order should be triggered based on current price."""
        if self.status != CustomOrderStatus.WAITING:
            return False

        # Update highest price if we see a new high
        if current_price > self.highest_price:
            self.highest_price = current_price
            return False

        # Get trigger price
        trigger_price = self.get_trigger_price()
        if trigger_price is None:
            return False

        # Check if conditions are met
        return current_price <= trigger_price and current_price >= self.min_price and self.highest_price >= self.min_price


@dataclass
class CustomTrailingStopBuyOrder:
    # todo - this dataclass should inherit from BaseCustomOrder
    """Represents a trailing stop buy order."""

    id: str
    stock_code: str
    max_price: float
    quantity: int
    lowest_price: float = float(1e10)
    status: CustomOrderStatus = CustomOrderStatus.WAITING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_checked_price: Optional[float] = None
    last_check_time: Optional[datetime] = None
    error_message: Optional[str] = None
    comments: Optional[str] = None

    trailing_amount: Optional[float] = None
    trailing_percent: Optional[float] = None

    @classmethod
    def create(
        cls,
        stock_code: str,
        max_price: float,
        quantity: int,
        trailing_amount: Optional[float] = None,
        trailing_percent: Optional[float] = None,
    ) -> "CustomTrailingStopBuyOrder":
        """Create a new trailing stop buy order with validation."""
        if trailing_amount is not None and trailing_percent is not None:
            raise ValueError("Cannot specify both trailing_amount and trailing_percent")
        if trailing_amount is None and trailing_percent is None:
            raise ValueError("Must specify either trailing_amount or trailing_percent")
        if trailing_amount is not None and trailing_amount <= 0:
            raise ValueError("Trailing amount must be positive")
        if trailing_percent is not None and (trailing_percent <= 0 or trailing_percent >= 100):
            raise ValueError("Trailing percent must be between 0 and 100")
        if max_price <= 0:
            raise ValueError("Maximum price must be positive")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        return cls(
            id=str(uuid4()),
            stock_code=stock_code,
            max_price=max_price,
            quantity=quantity,
            trailing_amount=trailing_amount,
            trailing_percent=trailing_percent,
        )

    def update_lowest_price(self, current_price: float) -> None:
        """Update the lowest price if current price is lower."""
        if self.lowest_price == float(1e10):
            self.lowest_price = current_price
        else:
            self.lowest_price = min(self.lowest_price, current_price)

    def get_trigger_price(self) -> Optional[float]:
        """Calculate the price that would trigger this order."""
        if self.lowest_price == float(1e10):
            return None

        if self.trailing_amount is not None:
            return self.lowest_price + self.trailing_amount
        elif self.trailing_percent is not None:
            return self.lowest_price * (1 + self.trailing_percent / 100)
        return None

    def should_trigger(self, current_price: float) -> bool:
        """Check if the order should be triggered based on current price."""
        if self.status != CustomOrderStatus.WAITING:
            return False

        self.update_lowest_price(current_price)

        # Get trigger price
        trigger_price = self.get_trigger_price()
        if trigger_price is None:
            return False

        # Check if conditions are met
        return current_price <= trigger_price and current_price <= self.max_price and self.lowest_price <= self.max_price
