"""Manager for trailing stop orders."""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

from src.core.moomoo_client import MoomooClient
from src.core.orders.models import (
    CustomOrderStatus,
    CustomTrailingStopBuyOrder,
    CustomTrailingStopSellOrder,
)
from src.core.orders.repositories import TrailingStopOrderRepository
from src.core.orders.services import (
    OrderService,
    TrailingStopBuyOrderService,
    TrailingStopSellOrderService,
)
from src.core.utilities import get_logger

log = get_logger(__name__)


OrderType = Union[CustomTrailingStopSellOrder, CustomTrailingStopBuyOrder]


class OrderManager:
    """Manages trailing stop orders and their execution."""

    def __init__(self, check_interval_seconds: float = 15.0):
        """Initialize the order manager.

        Args:
            check_interval: How often to check prices in seconds
        """
        self.is_simulated_env = False
        self.orders: Dict[str, OrderType] = {}
        self.services: Dict[Type, OrderService] = {
            CustomTrailingStopSellOrder: TrailingStopSellOrderService(
                self.is_simulated_env
            ),
            CustomTrailingStopBuyOrder: TrailingStopBuyOrderService(
                self.is_simulated_env
            ),
        }
        self.repository = TrailingStopOrderRepository(self._get_storage_path())
        self.check_interval = check_interval_seconds
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._load_orders()

    def _get_storage_path(self) -> Path:
        """Get the path to the order storage file."""
        return Path(__file__).parents[3] / "data" / "orders.json"

    def _load_orders(self) -> None:
        """Load orders from persistent storage."""
        try:
            self.orders = self.repository.load()
        except Exception as e:
            log.error(f"Failed to load orders: {e}")
            self.orders = {}

    def _save_orders(self) -> None:
        """Save orders to persistent storage."""
        try:
            self.repository.save(self.orders)
        except Exception as e:
            log.error(f"Failed to save orders: {e}")

    def add_order(self, order: OrderType) -> None:
        """Add a new trailing stop order."""
        positions = MoomooClient.get_current_positions()
        if positions is None:
            log.error("Unable to get positions")
            return

        service = self.services[type(order)]
        service.validate_new_order(order, positions)
        self.orders[order.id] = order
        self._save_orders()
        log.info(f"Added new trailing stop order: {order}")

    def cancel_order(self, order_id: str) -> None:
        """Cancel a trailing stop order."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        service = self.services[type(order)]
        if not service.can_cancel_order(order):
            raise ValueError(f"Cannot cancel order in status {order.status}")

        if isinstance(order, CustomTrailingStopSellOrder):
            order.status = CustomOrderStatus.CANCELLED
        else:
            order.status = CustomOrderStatus.CANCELLED

        order.updated_at = datetime.now()
        self._save_orders()
        log.info(f"Cancelled order: {order}")

    def get_order(self, order_id: str) -> Optional[OrderType]:
        """Get a specific order by ID."""
        return self.orders.get(order_id)

    def get_active_orders(self) -> List[OrderType]:
        """Get all active (waiting) orders."""
        return [
            order
            for order in self.orders.values()
            if self.services[type(order)].is_order_waiting(order)
        ]

    def get_all_orders(self) -> List[OrderType]:
        """Get all orders."""
        return list(self.orders.values())

    def _check_and_execute_orders(self):
        positions = MoomooClient.get_current_positions()
        if not positions:
            log.error("Unable to get positions")
            return

        active_orders = self.get_active_orders()

        for order in active_orders:
            try:
                service = self.services[type(order)]
                current_price = service.get_current_price(order, positions)

                # Update order tracking
                order.last_checked_price = current_price
                order.last_check_time = datetime.now()
                order.updated_at = datetime.now()

                if not current_price:
                    log.warning(f"unable to get price data for order {order.id}")
                    continue

                # Check if order should trigger
                if order.should_trigger(current_price):
                    order.comments = f"Triggered at {current_price}"
                    service.execute_order(order)

            except Exception as e:
                log.error(f"Error processing order {order.id}: {e}")
                service = self.services[type(order)]
                service.set_error_status(order, str(e))

        self._save_orders()

    def _monitor_loop(self) -> None:
        """Main monitoring loop for checking orders."""
        while self.running:
            log.debug("polling..")
            try:
                self._check_and_execute_orders()
            except Exception as e:
                log.error(f"Error in monitor loop: {e}")
            time.sleep(self.check_interval)

    def start(self) -> None:
        """Start the order monitoring thread."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        log.info("Order manager started")

    def stop(self) -> None:
        """Stop the order monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None
        log.info("Order manager stopped")
