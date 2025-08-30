import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.external_data_services.stock_data.yfinance import get_stock_price
from src.core.orders.models import CustomOrderStatus, RangeBucketBuyOrder
from src.core.orders.services import RangeBucketBuyOrderService
from src.core.utilities import get_logger

log = get_logger(__name__)


@pytest.fixture
def service():
    return RangeBucketBuyOrderService(is_simulated_env=True)


@pytest.fixture
def basic_order():
    return RangeBucketBuyOrder(id="test-id", stock_code="AAPL", quantity=100, start_price=150.0, end_price=160.0, num_buckets=3)


class TestRangeBucketBuyOrderService:
    def test_validate_new_order(self, service, basic_order):
        # Validation should pass without raising exceptions
        service.validate_new_order(basic_order, [])

    def test_can_cancel_order(self, service, basic_order):
        # Should be cancellable when waiting with remaining buckets
        assert service.can_cancel_order(basic_order) is True

        # Should not be cancellable when completed
        basic_order.status = CustomOrderStatus.COMPLETED
        assert service.can_cancel_order(basic_order) is False

        # Should not be cancellable when no remaining buckets
        basic_order.status = CustomOrderStatus.WAITING
        for price in basic_order.buckets:
            basic_order.mark_bucket_triggered(price)
        assert service.can_cancel_order(basic_order) is False

    def test_is_order_waiting(self, service, basic_order):
        # Should be waiting initially
        assert service.is_order_waiting(basic_order) is True

        # Should not be waiting when completed
        basic_order.status = CustomOrderStatus.COMPLETED
        assert service.is_order_waiting(basic_order) is False

        # Should not be waiting when no remaining buckets
        basic_order.status = CustomOrderStatus.WAITING
        for price in basic_order.buckets:
            basic_order.mark_bucket_triggered(price)
        assert service.is_order_waiting(basic_order) is False

    def test_get_current_price_from_positions(self, service, basic_order):
        mock_position = MagicMock()
        mock_position.code = "AAPL"
        mock_position.nominal_price = 155.0
        positions = [mock_position]

        price = service.get_current_price(basic_order, positions)
        assert price == 155.0

    @patch("src.core.orders.services.get_stock_price")
    def test_get_current_price_from_yfinance(self, mock_get_price, service, basic_order):
        mock_get_price.return_value = 157.0
        price = service.get_current_price(basic_order, [])
        assert price == 157.0
        mock_get_price.assert_called_once_with("AAPL")

    @patch("src.core.moomoo_client.MoomooClient.get_trade_context")
    def test_execute_order(self, mock_trade_context, service, basic_order):
        # Mock the trade context
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_ctx
        mock_ctx.unlock_trade.return_value = (0, None)  # RET_OK = 0
        mock_ctx.place_order.return_value = (0, None)  # RET_OK = 0
        mock_trade_context.return_value = mock_ctx

        trigger_price = basic_order.get_trigger_price()

        # Execute order
        service.execute_order(basic_order)

        # Verify order placement
        mock_ctx.place_order.assert_called_once()
        args, kwargs = mock_ctx.place_order.call_args
        assert kwargs["qty"] == basic_order.quantity // len(basic_order.buckets)
        assert kwargs["code"] == "AAPL"

        assert basic_order.triggered_buckets == [trigger_price]

    @patch("src.core.moomoo_client.MoomooClient.get_trade_context")
    def test_execute_order_failure(self, mock_trade_context, service, basic_order):
        # Mock the trade context with failure
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_ctx
        mock_ctx.unlock_trade.return_value = (0, None)
        mock_ctx.place_order.return_value = (1, "Error message")  # Non-zero return code
        mock_trade_context.return_value = mock_ctx

        # Execute order should raise exception
        with pytest.raises(Exception) as exc_info:
            service.execute_order(basic_order)

        assert "Failed to place order" in str(exc_info.value)
        assert basic_order.status == CustomOrderStatus.ERROR
        assert basic_order.error_message is not None

    def test_set_error_status(self, service, basic_order):
        service.set_error_status(basic_order, "Test error")
        assert basic_order.status == CustomOrderStatus.ERROR
        assert basic_order.error_message == "Test error"
        assert isinstance(basic_order.updated_at, datetime)
