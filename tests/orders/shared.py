from src.core.orders.models2 import BaseCustomOrderModel


class TestOrderModel(BaseCustomOrderModel):
    """Concrete implementation of BaseCustomOrderModel for testing."""

    __tablename__ = "test_order_model"

    def get_trigger_price(self):
        return 100.0

    def should_trigger(self, current_price):
        return current_price >= 100.0
