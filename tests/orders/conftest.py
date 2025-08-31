# Create a concrete subclass for testing the abstract base class
from core.orders.models2 import BaseCustomOrderModel


class TestOrderModel(BaseCustomOrderModel):
    """Concrete implementation of BaseCustomOrderModel for testing."""

    def get_trigger_price(self):
        return 100.0

    def should_trigger(self, current_price):
        return current_price >= 100.0
