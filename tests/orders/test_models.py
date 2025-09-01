from datetime import datetime, timedelta, timezone

import pytest

from src.core.orders.models2 import (
    BaseCustomOrderModel,
    CustomOrderStatus,
    PriceBucketModel,
    RangeBucketBuyOrderModel,
)
from tests.orders.shared import TestOrderModel


class TestBaseCustomOrderModel:
    def test_table_name_generation(self):
        """Test that the tablename is correctly generated from the class name."""
        assert TestOrderModel.__tablename__ == "test_order_model"

    def test_model_init(self, db_session):
        """Test that a model instance can be created with required fields."""
        order = TestOrderModel(id="test-id-123", stock_code="AAPL", quantity=10)

        db_session.add(order)
        db_session.commit()

        saved_order = db_session.query(TestOrderModel).filter_by(id="test-id-123").first()
        assert saved_order is not None
        assert saved_order.stock_code == "AAPL"
        assert saved_order.quantity == 10
        assert saved_order.status == CustomOrderStatus.WAITING
        assert saved_order.last_checked_price is None
        assert saved_order.error_message is None

    def test_validate_positive_quantity(self):
        """Test that validation fails with non-positive quantity."""
        order = TestOrderModel(id="test-id", stock_code="AAPL", quantity=0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            order.validate()

    def test_abstract_methods(self):
        """Test concrete implementation of abstract methods."""
        order = TestOrderModel(id="test-id", stock_code="AAPL", quantity=10)

        assert order.get_trigger_price() == 100.0
        assert order.should_trigger(100.0) is True
        assert order.should_trigger(99.9) is False

    def test_model_updates(self, db_session):
        """Test that model fields can be updated."""
        # Create and save order
        order = TestOrderModel(id="test-id-456", stock_code="TSLA", quantity=5)
        db_session.add(order)
        db_session.commit()

        # Update order
        saved_order = db_session.query(TestOrderModel).filter_by(id="test-id-456").first()
        saved_order.last_checked_price = 150.25
        saved_order.last_check_time = datetime.now()
        saved_order.status = CustomOrderStatus.TRIGGERED
        db_session.commit()

        # Verify updates
        updated_order = db_session.query(TestOrderModel).filter_by(id="test-id-456").first()
        assert updated_order.last_checked_price == 150.25
        assert updated_order.status == CustomOrderStatus.TRIGGERED
        assert updated_order.last_check_time is not None

    def test_error_handling(self, db_session):
        """Test error message handling."""
        order = TestOrderModel(id="test-id-789", stock_code="GOOG", quantity=3, error_message="Connection timeout")
        db_session.add(order)
        db_session.commit()

        saved_order = db_session.query(TestOrderModel).filter_by(id="test-id-789").first()
        assert saved_order.error_message == "Connection timeout"

        # Update error message
        saved_order.error_message = None
        db_session.commit()

        updated_order = db_session.query(TestOrderModel).filter_by(id="test-id-789").first()
        assert updated_order.error_message is None

    def test_missing_created_updated_timestamps(self):
        """Test that the model is missing created_at and updated_at fields."""
        order = TestOrderModel(id="test-id", stock_code="AAPL", quantity=10)
        assert not hasattr(order, "created_at")
        assert not hasattr(order, "updated_at")


class TestRangeBucketBuyOrderModel:
    def test_model_init_with_num_buckets(self):
        """Test model initialization with number of buckets specified."""
        order = RangeBucketBuyOrderModel(id="range-test-1", stock_code="AAPL", quantity=5, start_price=120.0, end_price=130.0, num_buckets=5)

        assert len(order.buckets) == 5
        assert order.buckets[0].price == 120.0
        assert order.buckets[-1].price == 130.0
        assert order.buckets[2].price == 125.0

    def test_model_init_with_bucket_size(self):
        """Test model initialization with bucket size specified."""
        order = RangeBucketBuyOrderModel(id="range-test-2", stock_code="MSFT", quantity=10, start_price=200.0, end_price=210.0, bucket_size=2.0)

        assert len(order.buckets) == 6  # 200, 202, 204, 206, 208, 210
        assert order.buckets[0].price == 200.0
        assert order.buckets[-1].price == 210.0

    def test_smart_rounding_in_bucket_generation(self):
        """Test that prices are rounded according to their magnitude."""
        # Low-price stock (rounds to 4 decimals)
        low_price_order = RangeBucketBuyOrderModel(id="range-test-3", stock_code="PENNY", quantity=100, start_price=0.5, end_price=0.6, num_buckets=3)

        # Mid-price stock (rounds to 3 decimals)
        mid_price_order = RangeBucketBuyOrderModel(id="range-test-4", stock_code="MID", quantity=50, start_price=5.0, end_price=6.0, num_buckets=3)

        # High-price stock (rounds to 1 decimal)
        high_price_order = RangeBucketBuyOrderModel(
            id="range-test-5", stock_code="EXPENSIVE", quantity=1, start_price=500.0, end_price=600.0, num_buckets=3
        )

        assert len(low_price_order.buckets) == 3
        assert len(mid_price_order.buckets) == 3
        assert len(high_price_order.buckets) == 3

        # Check precision of rounded values
        assert f"{low_price_order.buckets[1].price:.5f}"[-1] == "0"  # 4 decimal precision
        assert f"{mid_price_order.buckets[1].price:.4f}"[-1] == "0"  # 3 decimal precision
        assert f"{high_price_order.buckets[1].price:.2f}"[-1] == "0"  # 1 decimal precision

    def test_validation_rules(self):
        """Test that validation rules work correctly."""
        # Test negative price validation
        with pytest.raises(ValueError, match="start_price must be positive"):
            RangeBucketBuyOrderModel(id="invalid-1", stock_code="AAPL", quantity=5, start_price=-10.0, end_price=100.0, num_buckets=5)

        # Test start_price >= end_price validation
        with pytest.raises(ValueError, match="start_price must be less than end_price"):
            order = RangeBucketBuyOrderModel(id="invalid-2", stock_code="AAPL", quantity=5, start_price=100.0, end_price=100.0, num_buckets=5)
            order.validate()

        # Test num_buckets and bucket_size mutual exclusivity
        with pytest.raises(ValueError, match="Specify only one: num_buckets or bucket_size"):
            order = RangeBucketBuyOrderModel(
                id="invalid-3", stock_code="AAPL", quantity=5, start_price=100.0, end_price=110.0, num_buckets=5, bucket_size=2.0
            )
            order.validate()

        # Test neither num_buckets nor bucket_size specified
        with pytest.raises(ValueError, match="Must specify either num_buckets or bucket_size"):
            order = RangeBucketBuyOrderModel(
                id="invalid-4",
                stock_code="AAPL",
                quantity=5,
                start_price=100.0,
                end_price=110.0,
            )
            order.validate()

    def test_progress_property(self):
        """Test that progress property correctly calculates completion percentage."""
        order = RangeBucketBuyOrderModel(id="progress-test", stock_code="AAPL", quantity=5, start_price=100.0, end_price=110.0, num_buckets=4)

        # Initially 0% complete
        assert order.progress == 0.0

        # Mark one bucket as triggered (25% complete)
        order.buckets[0].is_triggered = True
        assert order.progress == 25.0

        # Mark two buckets as triggered (50% complete)
        order.buckets[1].is_triggered = True
        assert order.progress == 50.0

        # All buckets triggered (100% complete)
        for bucket in order.buckets:
            bucket.is_triggered = True
        assert order.progress == 100.0

        # Edge case: empty buckets list
        order.buckets.clear()
        assert order.progress == 100.0

    def test_bucket_ordering(self):
        """Test that buckets maintain their order in the collection."""
        order = RangeBucketBuyOrderModel(id="order-test", stock_code="AAPL", quantity=5, start_price=100.0, end_price=110.0, num_buckets=5)

        # Check initial positions
        for i, bucket in enumerate(order.buckets):
            assert bucket.position == i

        # Remove a bucket from the middle and check positions update
        removed_bucket = order.buckets.pop(2)
        for i, bucket in enumerate(order.buckets):
            assert bucket.position == i

    def test_db_persistence(self, db_session):
        """Test database persistence and retrieval."""
        # Create and save an order with buckets
        order = RangeBucketBuyOrderModel(id="db-test", stock_code="AAPL", quantity=5, start_price=100.0, end_price=110.0, num_buckets=5)

        db_session.add(order)
        db_session.commit()

        # Retrieve the order
        saved_order = db_session.query(RangeBucketBuyOrderModel).filter_by(id="db-test").first()
        assert saved_order is not None
        assert saved_order.stock_code == "AAPL"
        assert saved_order.quantity == 5
        assert saved_order.start_price == 100.0
        assert saved_order.end_price == 110.0
        assert saved_order.num_buckets == 5
        assert len(saved_order.buckets) == 5

        # Modify buckets and check changes persist
        saved_order.buckets[0].is_triggered = True
        saved_order.buckets[0].trigger_time = datetime.now(tz=timezone.utc)
        db_session.commit()

        # Retrieve again
        updated_order = db_session.query(RangeBucketBuyOrderModel).filter_by(id="db-test").first()
        assert updated_order.buckets[0].is_triggered is True
        assert updated_order.buckets[0].trigger_time is not None
        assert updated_order.progress == 20.0  # 1/5 buckets triggered

        # Test cascade delete
        db_session.delete(updated_order)
        db_session.commit()

        # Verify buckets were deleted
        buckets = db_session.query(PriceBucketModel).filter_by(order_id="db-test").all()
        assert len(buckets) == 0
        assert len(buckets) == 0
