from datetime import datetime

import pytest

from src.core.orders.models import BaseCustomOrder, CustomOrderStatus, RangeBucketBuyOrder


class MockCustomOrder(BaseCustomOrder):
    """Minimal concrete implementation for testing BaseCustomOrder."""

    def get_trigger_price(self) -> float:
        return 100.0

    def should_trigger(self, current_price: float) -> bool:
        return current_price >= 100.0


class TestCustomOrder:
    def test_base_order_validation_succeeds(self):
        """Test that validation passes with valid quantity."""
        object = MockCustomOrder(id="123", stock_code="AAPL", quantity=100)
        object.validate()

    def test_base_order_validation_fails_zero(self):
        """Test that validation fails with zero quantity."""
        object = MockCustomOrder(id="123", stock_code="AAPL", quantity=0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            object.validate()

    def test_base_order_validation_fails_negative(self):
        object = MockCustomOrder(id="123", stock_code="AAPL", quantity=-10)
        """Test that validation fails with negative quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            object.validate()

    def test_base_order_default_status(self):
        """Test default order status is WAITING."""
        order = MockCustomOrder(id="123", stock_code="AAPL", quantity=100)
        assert order.status == CustomOrderStatus.WAITING

    def test_base_order_timestamps(self):
        """Test timestamps are initialized."""
        before = datetime.now()
        order = MockCustomOrder(id="123", stock_code="AAPL", quantity=100)
        after = datetime.now()

        assert before <= order.created_at <= after
        assert before <= order.updated_at <= after

    def test_base_order_default_fields(self):
        """Test optional fields are initialized to defaults."""
        order = MockCustomOrder(id="123", stock_code="AAPL", quantity=100)

        assert order.last_checked_price is None
        assert order.last_check_time is None
        assert order.error_message is None
        assert order.comments is None

    def test_base_order_required_fields(self):
        """Test required fields are set correctly."""
        order = MockCustomOrder(id="test_id", stock_code="AAPL", quantity=100)

        assert order.id == "test_id"
        assert order.stock_code == "AAPL"
        assert order.quantity == 100

    def test_base_order_abstract_methods(self):
        """Test concrete implementation of abstract methods."""
        order = MockCustomOrder(id="123", stock_code="AAPL", quantity=100)

        assert order.get_trigger_price() == 100.0
        assert order.should_trigger(100.0) is True
        assert order.should_trigger(99.9) is False


class TestRangeBucketOrder:
    def test_create_with_num_buckets(self):
        """Test creation with number of buckets specified."""
        order = RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, num_buckets=3)
        assert len(order.buckets) == 3
        assert order.buckets == [100.0, 105.0, 110.0]

    def test_create_with_bucket_size(self):
        """Test creation with bucket size specified."""
        order = RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, bucket_size=5.0)
        assert len(order.buckets) == 3
        assert order.buckets == [100.0, 105.0, 110.0]

    def test_validation_fails_invalid_prices(self):
        """Test validation fails when start price >= end price."""
        with pytest.raises(ValueError, match="start_price must be less than end_price"):
            RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=110.0, end_price=100.0, num_buckets=3)

    def test_validation_fails_both_params(self):
        """Test validation fails when both num_buckets and bucket_size specified."""
        with pytest.raises(ValueError, match="Specify only one: num_buckets or bucket_size"):
            RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, num_buckets=3, bucket_size=5.0)

    def test_validation_fails_no_params(self):
        """Test validation fails when neither num_buckets nor bucket_size specified."""
        with pytest.raises(ValueError, match="Must specify either num_buckets or bucket_size"):
            RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0)

    def test_get_trigger_price(self):
        """Test get_trigger_price returns next untriggered bucket."""
        order = RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, num_buckets=3)
        assert order.get_trigger_price() == 100.0

        # Mark first bucket as triggered
        order.mark_bucket_triggered(100.0)
        assert order.get_trigger_price() == 105.0

        # Mark all buckets as triggered
        order.mark_bucket_triggered(105.0)
        order.mark_bucket_triggered(110.0)
        assert order.get_trigger_price() is None

    def test_should_trigger(self):
        """Test should_trigger with price matching and tolerance."""
        order = RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, num_buckets=3)

        # Exact match
        assert order.should_trigger(100.0) is True

        # Within tolerance
        assert order.should_trigger(100.0001) is True
        assert order.should_trigger(99.9999) is True

        # Outside tolerance
        assert order.should_trigger(100.5) is False

    def test_mark_bucket_triggered(self):
        """Test marking buckets as triggered."""
        order = RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, num_buckets=3)

        # Mark first bucket
        order.mark_bucket_triggered(100.0)
        assert 100.0 in order.triggered_buckets
        assert order.status == CustomOrderStatus.WAITING

        # Mark invalid bucket
        order.mark_bucket_triggered(102.0)
        assert 102.0 not in order.triggered_buckets

        # Mark all buckets
        order.mark_bucket_triggered(105.0)
        order.mark_bucket_triggered(110.0)
        assert order.status == CustomOrderStatus.COMPLETED

    def test_remaining_buckets(self):
        """Test getting remaining untriggered buckets."""
        order = RangeBucketBuyOrder(id="test", stock_code="AAPL", quantity=100, start_price=100.0, end_price=110.0, num_buckets=3)

        assert order.remaining_buckets() == [100.0, 105.0, 110.0]

        order.mark_bucket_triggered(100.0)
        assert order.remaining_buckets() == [105.0, 110.0]

        order.mark_bucket_triggered(110.0)
        assert order.remaining_buckets() == [105.0]
