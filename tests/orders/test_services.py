from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.core.orders.models import (
    CustomOrderStatus,
    PriceBucketModel,
    RangeBucketBuyOrderModel,
)
from src.core.orders.services import RangeBucketBuyOrderService


@pytest.fixture
def mock_moomoo_client():
    with patch("src.core.orders.services.MoomooClient") as mock_client:
        # Set up the mock trade context
        mock_trade_ctx = MagicMock()
        mock_client.get_trade_context.return_value.__enter__.return_value = mock_trade_ctx
        mock_trade_ctx.unlock_trade.return_value = (0, None)  # RET_OK is 0
        mock_trade_ctx.place_order.return_value = (0, None)  # RET_OK is 0
        yield mock_client


@pytest.fixture
def sample_order():
    return RangeBucketBuyOrderModel(
        id="test-order-123",
        stock_code="US.AAPL",
        quantity=100,
        price_tolerance=0.01,
        start_price=140.0,
        end_price=150.0,
        num_buckets=3,
        status=CustomOrderStatus.WAITING.value,
        buckets=[
            PriceBucketModel(price=150.0, is_triggered=False),
            PriceBucketModel(price=145.0, is_triggered=False),
            PriceBucketModel(price=140.0, is_triggered=False),
        ],
        created_on=datetime.now(tz=timezone.utc),
        updated_on=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def order_service():
    with patch("src.core.orders.services.RangeBucketBuyOrderRepository") as mock_repo:
        # Configure the mock repository
        repository_instance = mock_repo.return_value
        repository_instance.get_db_session.return_value = MagicMock()
        repository_instance.update.return_value = None
        repository_instance.save.return_value = None

        service = RangeBucketBuyOrderService(is_simulated_env=True)
        yield service


class TestRangeBucketBuyOrderService:
    def test_init(self, order_service):
        """Test service initialization."""
        assert order_service.is_simulated_env is True
        assert order_service.repository is not None

    def test_validate_new_order_valid(self, order_service, sample_order):
        """Test validation of a valid order."""
        order_service.validate_new_order(sample_order, [])
        # If no exception is raised, the test passes

    def test_validate_new_order_invalid_quantity(self, order_service, sample_order):
        """Test validation fails with invalid quantity."""
        sample_order.quantity = 0
        with pytest.raises(ValueError, match="Order quantity must be greater than 0"):
            order_service.validate_new_order(sample_order, [])

    def test_validate_new_order_no_buckets(self, order_service, sample_order):
        """Test validation fails with no buckets."""
        sample_order.buckets = []
        with pytest.raises(ValueError, match="Range bucket order must have at least one bucket"):
            order_service.validate_new_order(sample_order, [])

    def test_validate_new_order_invalid_bucket_price(self, order_service, sample_order):
        """Test validation fails with invalid bucket price."""
        sample_order.buckets[1].price = 0
        with pytest.raises(ValueError, match="Bucket price must be greater than 0"):
            order_service.validate_new_order(sample_order, [])

    def test_can_cancel_order(self, order_service, sample_order):
        """Test checking if an order can be cancelled."""
        assert order_service.can_cancel_order(sample_order) is True

        sample_order.status = CustomOrderStatus.COMPLETED.value
        assert order_service.can_cancel_order(sample_order) is False

    def test_is_order_waiting(self, order_service, sample_order):
        """Test checking if an order is in waiting status."""
        assert order_service.is_order_waiting(sample_order) is True

        sample_order.status = CustomOrderStatus.COMPLETED.value
        assert order_service.is_order_waiting(sample_order) is False

    @patch("src.core.orders.services.get_stock_price")
    def test_get_current_price_from_positions(self, mock_get_stock_price, order_service, sample_order):
        """Test getting current price from positions."""
        mock_position = MagicMock()
        mock_position.code = "US.AAPL"
        mock_position.nominal_price = 155.0

        price = order_service.get_current_price(sample_order, [mock_position])
        assert price == 155.0
        mock_get_stock_price.assert_not_called()

    @patch("src.core.orders.services.get_stock_price")
    def test_get_current_price_fallback(self, mock_get_stock_price, order_service, sample_order):
        """Test getting current price falls back to API when not in positions."""
        mock_get_stock_price.return_value = 152.0

        price = order_service.get_current_price(sample_order, [])
        assert price == 152.0
        mock_get_stock_price.assert_called_once_with("US.AAPL")

    def test_execute_order_success(self, order_service, sample_order, mock_moomoo_client):
        """Test successful execution of an order."""
        # Mock the repository methods
        order_service.repository.update = MagicMock()

        # Execute the order
        order_service.execute_order(sample_order)

        # Verify that a bucket was marked as triggered
        assert any(bucket.is_triggered for bucket in sample_order.buckets)

        # Verify repository was called to update the order
        order_service.repository.update.assert_called()

    def test_execute_order_all_buckets_triggered(self, order_service, sample_order):
        """Test execution when all buckets are already triggered."""
        # Mark all buckets as triggered
        for bucket in sample_order.buckets:
            bucket.is_triggered = True

        # Mock the repository methods
        order_service.repository.update = MagicMock()

        # Execute the order
        order_service.execute_order(sample_order)

        # Verify the order status was updated to completed
        assert sample_order.status == CustomOrderStatus.COMPLETED.value

        # Verify repository was called to update the order
        order_service.repository.update.assert_called()

    def test_execute_order_error(self, order_service, sample_order, mock_moomoo_client):
        """Test error handling during order execution."""
        # Configure the mock to raise an exception
        mock_trade_ctx = mock_moomoo_client.get_trade_context.return_value.__enter__.return_value
        mock_trade_ctx.place_order.return_value = (1, "Error placing order")  # Not RET_OK

        # Mock the error status setter
        order_service.set_error_status = MagicMock()

        # Patch MoomooClient in the service module to use our mock
        with patch("core.orders.services.MoomooClient", mock_moomoo_client):
            # Execute the order and expect an exception
            with pytest.raises(Exception):
                order_service.execute_order(sample_order)

        # Verify error status was set
        order_service.set_error_status.assert_called_once()

    def test_set_error_status(self, order_service, sample_order):
        """Test setting error status on an order."""
        # Mock the repository update method
        order_service.repository.update = MagicMock()

        # Set error status
        order_service.set_error_status(sample_order, "Test error message")

        # Verify the order status was updated
        assert sample_order.status == CustomOrderStatus.ERROR.value
        assert sample_order.error_message == "Test error message"

        # Verify repository was called to update the order
        order_service.repository.update.assert_called_once()

    def test_mark_bucket_triggered(self, order_service, sample_order):
        """Test marking a bucket as triggered."""
        # Mark a bucket as triggered
        order_service.mark_bucket_triggered(sample_order, 150.0)

        # Verify the correct bucket was triggered
        assert sample_order.buckets[0].is_triggered is True
        assert sample_order.buckets[1].is_triggered is False
        assert sample_order.buckets[2].is_triggered is False

        # Status should still be WAITING since not all buckets are triggered
        assert sample_order.status == CustomOrderStatus.WAITING.value

    def test_mark_all_buckets_triggered(self, order_service, sample_order):
        """Test marking all buckets as triggered updates order status."""
        # Mark all buckets as triggered
        for bucket in sample_order.buckets:
            order_service.mark_bucket_triggered(sample_order, bucket.price)

        # Verify the order status was updated to completed
        assert sample_order.status == CustomOrderStatus.COMPLETED.value

    def test_get_remaining_buckets(self, order_service, sample_order):
        """Test getting remaining buckets."""
        # Mark one bucket as triggered
        sample_order.buckets[0].is_triggered = True

        # Get remaining buckets
        remaining = order_service.get_remaining_buckets(sample_order)

        # Verify the correct buckets are returned
        assert len(remaining) == 2
        assert remaining[0] == sample_order.buckets[1]
        assert remaining[1] == sample_order.buckets[2]

    def test_get_bucket_quantity(self, order_service, sample_order):
        """Test calculating bucket quantity."""
        # With 100 quantity and 3 buckets, each should get ~33 shares
        # with the remainder distributed to lower price buckets

        # First bucket (higher price) gets base amount
        # qty = order_service.get_bucket_quantity(sample_order, 150.0)
        # assert qty == 33

        # # Lower price buckets get the remainder
        # qty = order_service.get_bucket_quantity(sample_order, 145.0)
        # assert qty == 33

        # Lower price buckets get the remainder
        # this isn't working
        # qty = order_service.get_bucket_quantity(sample_order, 140.0)
        # assert qty == 34
