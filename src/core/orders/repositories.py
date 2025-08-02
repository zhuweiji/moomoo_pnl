"""Repository classes for handling data persistence."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Generic, List, Optional, Type, TypeVar

from src.core.orders.models import (
    CustomOrderStatus,
    CustomTrailingStopBuyOrder,
    CustomTrailingStopSellOrder,
)
from src.core.utilities import get_logger

log = get_logger(__name__)


T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base class for repositories."""

    @abstractmethod
    def save(self, items: Dict[str, T]) -> None:
        """Save items to storage."""
        pass

    @abstractmethod
    def load(self) -> Dict[str, T]:
        """Load items from storage."""
        pass


class JsonFileRepository(Repository[T]):
    """Repository implementation that stores data in JSON files."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path

    def save(self, items: Dict[str, T]) -> None:
        """Save items to a JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            items_data = []
            log.debug(f"Saving items to {self.storage_path}")

            for item in items.values():
                item_dict = asdict(item)  # type: ignore

                # Convert datetime objects to ISO format strings
                for field in ["created_at", "updated_at", "last_check_time"]:
                    if field in item_dict and item_dict[field] is not None:
                        item_dict[field] = item_dict[field].isoformat()
                # Convert enum to string if present
                if "status" in item_dict:
                    item_dict["status"] = item_dict["status"].value
                item_dict["id"] = str(item_dict["id"])
                items_data.append(item_dict)

            with open(self.storage_path, "w") as f:
                json.dump(items_data, f, indent=2)
                log.debug(f"Saved {len(items_data)} items to {self.storage_path}")
        except Exception as e:
            log.error(f"Failed to save items: {e}")
            raise


class OrderRepository(JsonFileRepository[T]):
    """Repository for handling order persistence."""

    def __init__(self, storage_path: Path, order_types: Dict[str, Type[T]]):
        """Initialize the order repository.

        Args:
            storage_path: Path to the JSON storage file
            order_types: Mapping of order type identifiers to order classes
        """
        super().__init__(storage_path)
        self.order_types = order_types

    def load(self) -> Dict[str, T]:
        """Load orders from storage with proper type conversion."""
        log.warning(self.storage_path)
        if not self.storage_path.exists():
            return {}

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                orders: Dict[str, T] = {}

                for order_data in data:
                    # Convert string dates back to datetime
                    for field in ["created_at", "updated_at"]:
                        order_data[field] = datetime.fromisoformat(order_data[field])
                    if order_data.get("last_check_time"):
                        order_data["last_check_time"] = datetime.fromisoformat(
                            order_data["last_check_time"]
                        )

                    # Determine order type and create appropriate object
                    order_type = self._determine_order_type(order_data)
                    if order_type is None:
                        log.warning(f"Unknown order type for data: {order_data}")
                        continue

                    # Convert string status back to enum
                    order_data["status"] = self._get_status_enum(order_type)(
                        order_data["status"]
                    )

                    # Create order object
                    order = order_type(**order_data)
                    orders[order.id] = order  # type: ignore

                return orders
        except Exception as e:
            log.error(f"Failed to load orders: {e}")
            raise

    def _determine_order_type(self, order_data: dict) -> Optional[Type[T]]:
        """Determine the correct order type based on the order data."""
        if "min_price" in order_data:
            return self.order_types.get("sell")
        elif "max_price" in order_data:
            return self.order_types.get("buy")
        return None

    def _get_status_enum(self, order_type: Type[T]) -> Type:
        """Get the status enum type for the given order type."""
        if order_type == CustomTrailingStopSellOrder:
            return CustomOrderStatus
        elif order_type == CustomTrailingStopBuyOrder:
            return CustomOrderStatus
        raise ValueError(f"Unknown order type: {order_type}")


class TrailingStopOrderRepository(
    OrderRepository[CustomTrailingStopSellOrder | CustomTrailingStopBuyOrder]
):
    """Specific repository for trailing stop orders."""

    def __init__(self, storage_path: Path):
        super().__init__(
            storage_path,
            {"sell": CustomTrailingStopSellOrder, "buy": CustomTrailingStopBuyOrder},
        )
