from datetime import datetime

import pytest

from src.core.orders.models2 import CustomOrderStatus
from src.core.orders.repositories2 import BaseCustomOrderRepository
from tests.orders.shared import TestOrderModel


class TestOrderRepository(BaseCustomOrderRepository):
    model = TestOrderModel


@pytest.fixture
def order_repository():
    """Create an order repository."""
    return TestOrderRepository


@pytest.fixture
def test_order():
    """Create a sample test order."""
    return TestOrderModel(
        id="test-order-1",
        stock_code="AAPL",
        quantity=10,
        status=CustomOrderStatus.WAITING,
        last_checked_price=150.25,
        last_check_time=datetime.now(),
        error_message=None,
        comments="Test order",
    )


def test_create_order(db_session, order_repository, test_order):
    """Test creating an order."""
    # Create order
    order_repository.save([test_order], db_session)

    # Verify order was created
    saved_order = db_session.query(TestOrderModel).filter_by(id=test_order.id).first()
    assert saved_order is not None
    assert saved_order.id == test_order.id
    assert saved_order.stock_code == "AAPL"
    assert saved_order.quantity == 10
    assert saved_order.status == CustomOrderStatus.WAITING
    assert saved_order.comments == "Test order"


def test_get_by_id(db_session, order_repository, test_order):
    """Test retrieving an order by ID."""
    # Create order
    db_session.add(test_order)
    db_session.commit()

    # Retrieve order
    order = order_repository.get_by_id(test_order.id, db_session)
    assert order is not None
    assert order.id == test_order.id
    assert order.stock_code == "AAPL"


def test_get_all(db_session, order_repository, test_order):
    """Test retrieving all orders."""
    # Create multiple orders
    order1 = test_order
    order2 = TestOrderModel(id="test-order-2", stock_code="MSFT", quantity=5, status=CustomOrderStatus.WAITING)
    db_session.add_all([order1, order2])
    db_session.commit()

    # Retrieve all orders
    orders = order_repository.get_all(db_session)
    assert len(orders) == 2
    assert {o.id for o in orders} == {"test-order-1", "test-order-2"}


def test_update(db_session, order_repository, test_order):
    """Test updating an order."""
    # Create order
    db_session.add(test_order)
    db_session.commit()

    # Update order
    test_order.quantity = 20
    test_order.status = CustomOrderStatus.COMPLETED
    test_order.last_checked_price = 155.75
    order_repository.update(test_order, db_session)

    # Verify updates
    updated_order = db_session.query(TestOrderModel).filter_by(id=test_order.id).first()
    assert updated_order.quantity == 20
    assert updated_order.status == CustomOrderStatus.COMPLETED
    assert updated_order.last_checked_price == 155.75


def test_delete(db_session, order_repository, test_order):
    """Test deleting an order."""
    # Create order
    db_session.add(test_order)
    db_session.commit()

    # Delete order
    order_repository.delete(test_order.id, db_session)

    # Verify deletion
    deleted_order = db_session.query(TestOrderModel).filter_by(id=test_order.id).first()
    assert deleted_order is None


def test_get_by_status(db_session, order_repository, test_order):
    """Test retrieving orders by status."""
    # Create orders with different statuses
    order1 = test_order
    order2 = TestOrderModel(id="test-order-2", stock_code="MSFT", quantity=5, status=CustomOrderStatus.COMPLETED)
    db_session.add_all([order1, order2])
    db_session.commit()

    # Get orders by status
    waiting_orders = order_repository.get_by_status(CustomOrderStatus.WAITING, db_session)
    executed_orders = order_repository.get_by_status(CustomOrderStatus.COMPLETED, db_session)

    assert len(waiting_orders) == 1
    assert waiting_orders[0].id == "test-order-1"

    assert len(executed_orders) == 1
    assert executed_orders[0].id == "test-order-2"
    assert executed_orders[0].id == "test-order-2"
    assert executed_orders[0].id == "test-order-2"
