"""Manager for handling different types of orders."""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Type, Union

from src.core.moomoo_client import MoomooClient
from src.core.orders.models2 import (
    CustomOrderStatus,
    RangeBucketBuyOrderModel,
    TrailingStopBuyOrderModel,
    TrailingStopSellOrderModel,
)
from src.core.orders.services2 import (
    OrderService,
    RangeBucketBuyOrderService,
    TrailingStopBuyOrderService,
    TrailingStopSellOrderService,
)
from src.core.utilities import get_logger

log = get_logger(__name__)

# Define a union type for all supported order types
OrderType = Union[
    TrailingStopSellOrderModel,
    TrailingStopBuyOrderModel,
    RangeBucketBuyOrderModel,
]


class OrderManager:
    """Manages various order types and their execution."""

    def __init__(self, check_interval_seconds: float = 15.0, is_simulated_env: bool = False):
        """Initialize the order manager.

        Args:
            check_interval_seconds: How often to check prices in seconds
            is_simulated_env: Whether to use simulated trading environment
        """
        self.is_simulated_env = is_simulated_env
        self.check_interval = check_interval_seconds
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Initialize order services
        self.services: Dict[Type, OrderService] = {
            TrailingStopSellOrderModel: TrailingStopSellOrderService(self.is_simulated_env),
            TrailingStopBuyOrderModel: TrailingStopBuyOrderService(self.is_simulated_env),
            RangeBucketBuyOrderModel: RangeBucketBuyOrderService(self.is_simulated_env),
        }

    def add_order(self, order: OrderType) -> None:
        """Add a new order."""
        positions = MoomooClient.get_current_positions()
        if positions is None:
            log.error("Unable to get positions")
            return

        service = self.services[type(order)]
        service.validate_new_order(order, positions)

        # Save order to database using the service's repository
        repository = service.repository
        repository.save([order], repository.get_db_session())

        log.info(f"Added new order: {order.id} of type {type(order).__name__}")

    def cancel_order(self, order_id: str, order_type: Type) -> None:
        """Cancel an order.

        Args:
            order_id: The ID of the order to cancel
            order_type: The type of the order (class)
        """
        service = self.services[order_type]
        repository = service.repository

        # Get order from database
        order = repository.get_by_id(order_id, repository.get_db_session())
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if not service.can_cancel_order(order):
            raise ValueError(f"Cannot cancel order in status {order.status}")

        order.status = CustomOrderStatus.CANCELLED.value
        order.updated_on = datetime.now()

        # Update in database
        repository.update(order, repository.get_db_session())
        log.info(f"Cancelled order: {order.id}")

    def get_order(self, order_id: str, order_type: Type) -> Optional[OrderType]:
        """Get a specific order by ID and type."""
        service = self.services[order_type]
        repository = service.repository
        return repository.get_by_id(order_id, repository.get_db_session())

    def get_active_orders(self) -> List[OrderType]:
        """Get all active (waiting) orders from all repositories."""
        active_orders = []

        for order_type, service in self.services.items():
            repository = service.repository
            orders = repository.get_by_status(CustomOrderStatus.WAITING, repository.get_db_session())
            active_orders.extend(orders)

        return active_orders

    def get_all_orders(self, order_type: Optional[Type] = None) -> List[OrderType]:
        """Get all orders, optionally filtered by type."""
        if order_type:
            service = self.services[order_type]
            repository = service.repository
            return repository.get_all(repository.get_db_session())

        # Get all orders from all repositories
        all_orders = []
        for order_type, service in self.services.items():
            repository = service.repository
            orders = repository.get_all(repository.get_db_session())
            all_orders.extend(orders)

        return all_orders

    def _check_and_execute_orders(self):
        """Check all active orders and execute them if conditions are met."""
        positions = MoomooClient.get_current_positions()
        if not positions:
            log.error("Unable to get positions")
            return

        active_orders = self.get_active_orders()
        log.debug(f"Checking {len(active_orders)} active orders")

        for order in active_orders:
            try:
                service = self.services[type(order)]
                repository = service.repository
                current_price = service.get_current_price(order, positions)

                # Update order tracking
                order.last_checked_price = current_price
                order.last_check_time = datetime.now()
                order.updated_on = datetime.now()

                # Update in database first
                repository.update(order, repository.get_db_session())

                if not current_price:
                    log.warning(f"Unable to get price data for order {order.id}")
                    continue

                # Check if order should trigger
                if hasattr(order, "should_trigger") and order.should_trigger(current_price):
                    order.comments = f"Triggered at {current_price}"
                    service.execute_order(order)

            except Exception as e:
                log.error(f"Error processing order {order.id}: {e}", exc_info=True)
                service = self.services[type(order)]
                service.set_error_status(order, str(e))

    def _monitor_loop(self) -> None:
        """Main monitoring loop for checking orders."""
        while self.running:
            log.debug("Polling for order execution...")
            try:
                self._check_and_execute_orders()
            except Exception as e:
                log.error(f"Error in monitor loop: {e}", exc_info=True)
            time.sleep(self.check_interval)

    def start(self) -> None:
        """Start the order monitoring thread."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, name="OrderManagerMonitor")
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        log.info("Order manager started")

    def stop(self) -> None:
        """Stop the order monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)  # Wait up to 10 seconds
            self.monitor_thread = None
        log.info("Order manager stopped")
