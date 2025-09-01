import json
import math
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import mapped_column, relationship, validates

from src.core.database.custom_types import TZDateTime
from src.core.database.model import BaseModel


class CustomOrderStatus(Enum):
    """Status of a custom order."""

    WAITING = "waiting"  # Waiting for conditions to be met
    TRIGGERED = "triggered"  # Conditions met, market order being placed
    COMPLETED = "completed"  # Market order executed
    CANCELLED = "cancelled"  # Order was cancelled by user
    ERROR = "error"  # Error occurred during execution


class BaseCustomOrderModel(BaseModel):
    """SQLAlchemy base model for all custom stock orders."""

    __abstract__ = True

    # Core order fields
    id = mapped_column(String, primary_key=True)
    stock_code = mapped_column(String, nullable=False)
    quantity = mapped_column(Integer, nullable=False)

    # Status and timing
    status = mapped_column(SQLAEnum(CustomOrderStatus), default=CustomOrderStatus.WAITING, nullable=False)

    # Tracking fields
    last_checked_price = mapped_column(Float, nullable=True)
    last_check_time = mapped_column(DateTime, nullable=True)

    # Error handling and notes
    error_message = mapped_column(String, nullable=True)
    comments = mapped_column(String, nullable=True)

    def validate(self):
        """Validate common parameters for all order types."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

    def get_trigger_price(self):
        """Calculate the price that would trigger this order."""
        raise NotImplementedError("Subclasses must implement get_trigger_price()")

    def should_trigger(self, current_price):
        """Check if the order should be triggered based on current price."""
        raise NotImplementedError("Subclasses must implement should_trigger()")


class PriceBucketModel(BaseModel):
    """Model for individual price buckets within a range order."""

    __tablename__ = "price_bucket"

    id = mapped_column(Integer, primary_key=True)
    order_id = mapped_column(String, ForeignKey("range_bucket_buy_order.id"), nullable=False)
    price = mapped_column(Float, nullable=False)
    is_triggered = mapped_column(Boolean, default=False, nullable=False)
    trigger_time = mapped_column(TZDateTime, nullable=True)
    position = mapped_column(Integer, nullable=False)  # For maintaining bucket order

    def __repr__(self):
        status = "✓" if self.is_triggered else "○"
        return f"{status} ${self.price:.4f}"


class RangeBucketBuyOrderModel(BaseCustomOrderModel):
    """
    SQLAlchemy model for a custom order that buys across a range of prices divided into buckets.
    Either specify num_buckets or bucket_size, but not both.
    """

    __tablename__ = "range_bucket_buy_order"

    start_price = mapped_column(Float, nullable=False)
    end_price = mapped_column(Float, nullable=False)
    num_buckets = mapped_column(Integer, nullable=True)
    bucket_size = mapped_column(Float, nullable=True)
    price_tolerance = mapped_column(Float, nullable=False, default=1e-2)

    # Relationship to bucket data
    buckets = relationship(
        "PriceBucketModel", cascade="all, delete-orphan", order_by="PriceBucketModel.position", collection_class=ordering_list("position")
    )

    @validates("start_price", "end_price", "num_buckets", "bucket_size")
    def validate_fields(self, key, value):
        """Validate model fields."""
        if key == "start_price" or key == "end_price":
            if value <= 0:
                raise ValueError(f"{key} must be positive")
        return value

    def validate(self):
        """Validate all parameters for the order."""
        super().validate()

        if self.start_price >= self.end_price:
            raise ValueError("start_price must be less than end_price")

        if self.num_buckets is not None and self.bucket_size is not None:
            raise ValueError("Specify only one: num_buckets or bucket_size")

        if self.num_buckets is None and self.bucket_size is None:
            raise ValueError("Must specify either num_buckets or bucket_size")

    def _generate_buckets(self) -> None:
        """Generate the list of bucket prices and create bucket objects."""
        # Clear existing buckets if any
        self.buckets.clear()

        # Helper to round price according to price magnitude
        def smart_round(price: float) -> float:
            if price < 1:
                return round(price, 4)  # More precision for low-price stocks
            elif price < 10:
                return round(price, 3)
            elif price < 100:
                return round(price, 2)
            else:
                return round(price, 1)  # Less precision needed for high-price stocks

        if self.num_buckets:
            # Ensure we have exactly num_buckets including start and end prices
            step = (self.end_price - self.start_price) / (self.num_buckets - 1) if self.num_buckets > 1 else 0
            for i in range(self.num_buckets):
                price = smart_round(self.start_price + i * step)
                self.buckets.append(PriceBucketModel(price=price))
        else:
            assert self.bucket_size
            num_buckets = math.floor((self.end_price - self.start_price) / self.bucket_size) + 1
            for i in range(num_buckets):
                price = self.start_price + i * self.bucket_size
                if price <= self.end_price + 1e-8:
                    self.buckets.append(PriceBucketModel(price=smart_round(price)))

    def __init__(self, **kwargs):
        """Initialize the model and generate buckets."""
        super().__init__(**kwargs)

        self.validate()
        # Generate buckets if not provided
        if "buckets" not in kwargs or not kwargs["buckets"]:
            self._generate_buckets()

    def get_trigger_price(self) -> Optional[float]:
        """Return the next untriggered bucket price that should trigger."""
        for bucket in self.buckets:
            if not bucket.is_triggered:
                return bucket.price
        return None  # All buckets triggered

    def should_trigger(self, current_price: float) -> bool:
        """Check if current price matches an untriggered bucket with tolerance."""
        for bucket in self.buckets:
            if not bucket.is_triggered:
                if abs(current_price - bucket.price) <= self.price_tolerance:
                    return True
        return False

    @property
    def progress(self) -> float:
        """Return the progress as a percentage (0-100)."""
        total_buckets = len(self.buckets)
        if total_buckets == 0:
            return 100.0  # No buckets means complete

        triggered = sum(1 for bucket in self.buckets if bucket.is_triggered)
        return (triggered / total_buckets) * 100.0


class TrailingStopSellOrderModel(BaseCustomOrderModel):
    """
    SQLAlchemy model for a custom order that sells when price drops by a specified
    amount or percentage from its highest point.
    """

    __tablename__ = "trailing_stop_sell_order"

    min_price = mapped_column(Float, nullable=False)
    highest_price = mapped_column(Float, default=0, nullable=False)
    trailing_amount = mapped_column(Float, nullable=True)
    trailing_percent = mapped_column(Float, nullable=True)

    @validates("min_price", "trailing_amount", "trailing_percent")
    def validate_fields(self, key, value):
        """Validate model fields."""
        if key == "min_price" and value <= 0:
            raise ValueError("Minimum price must be positive")
        if key == "trailing_amount" and value is not None and value <= 0:
            raise ValueError("Trailing amount must be positive")
        if key == "trailing_percent" and value is not None and (value <= 0 or value >= 100):
            raise ValueError("Trailing percent must be between 0 and 100")
        return value

    def validate(self):
        """Validate all parameters for the order."""
        super().validate()

        if (self.trailing_amount is None and self.trailing_percent is None) or (
            self.trailing_amount is not None and self.trailing_percent is not None
        ):
            raise ValueError("Must specify exactly one of: trailing_amount or trailing_percent")

    def __init__(self, **kwargs):
        """Initialize the model with validation."""
        super().__init__(**kwargs)
        self.validate()

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


class TrailingStopBuyOrderModel(BaseCustomOrderModel):
    """
    SQLAlchemy model for a custom order that buys when price rises by a specified
    amount or percentage from its lowest point.
    """

    __tablename__ = "trailing_stop_buy_order"

    max_price = mapped_column(Float, nullable=False)
    lowest_price = mapped_column(Float, default=float(1e10), nullable=False)
    trailing_amount = mapped_column(Float, nullable=True)
    trailing_percent = mapped_column(Float, nullable=True)

    @validates("max_price", "trailing_amount", "trailing_percent")
    def validate_fields(self, key, value):
        """Validate model fields."""
        if key == "max_price" and value <= 0:
            raise ValueError("Maximum price must be positive")
        if key == "trailing_amount" and value is not None and value <= 0:
            raise ValueError("Trailing amount must be positive")
        if key == "trailing_percent" and value is not None and (value <= 0 or value >= 100):
            raise ValueError("Trailing percent must be between 0 and 100")
        return value

    def validate(self):
        """Validate all parameters for the order."""
        super().validate()

        if (self.trailing_amount is None and self.trailing_percent is None) or (
            self.trailing_amount is not None and self.trailing_percent is not None
        ):
            raise ValueError("Must specify exactly one of: trailing_amount or trailing_percent")

    def __init__(self, **kwargs):
        """Initialize the model with validation."""
        super().__init__(**kwargs)
        self.validate()

    def update_lowest_price(self, current_price: float) -> None:
        """Update the lowest price if current price is lower."""
        if self.lowest_price == float(1e10) or current_price < self.lowest_price:
            self.lowest_price = current_price

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
        return current_price >= trigger_price and current_price <= self.max_price and self.lowest_price <= self.max_price
