"""Repository classes for handling data persistence."""

from dataclasses import asdict
from typing import Collection, Dict, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy.orm import Session

from src.core.database import BaseRepository
from src.core.database.get_engine import SessionMaker
from src.core.orders.models import CustomOrderStatus
from src.core.orders.models2 import (
    BaseCustomOrderModel,
    RangeBucketBuyOrderModel,
    TrailingStopBuyOrderModel,
    TrailingStopSellOrderModel,
)
from src.core.utilities import get_logger

log = get_logger(__name__)


T = TypeVar("T", bound=BaseCustomOrderModel)


class BaseCustomOrderRepository(BaseRepository):
    model: Type[BaseCustomOrderModel] = None  # type: ignore

    @classmethod
    def save(cls, items: Collection[T], session: Session) -> None:
        """Save orders to the database.

        Args:
            items: Collection of orders to save
            session: Database session
        """
        for order in items:
            # Check if order already exists
            existing = session.query(cls.model).filter_by(id=order.id).first()
            if existing:
                # Update existing order
                cls._update_model_attributes(existing, order)
            else:
                # Add new order
                session.add(order)

        session.commit()

    @classmethod
    def update(cls, order: T, session: Session) -> None:
        """Update an existing order in the database.

        Args:
            order: The order to update
            session: Database session
        """
        existing = session.query(cls.model).filter_by(id=order.id).first()
        if existing:
            cls._update_model_attributes(existing, order)
            session.commit()
        else:
            log.warning(f"Attempted to update non-existent order: {order.id}")

    @classmethod
    def _update_model_attributes(cls, target: T, source: T) -> None:
        """Update attributes of target model from source model.

        Args:
            target: The model to update
            source: The model to copy attributes from
        """
        # Update direct attributes
        for c in source.__table__.columns:
            if c.name != "id":  # Don't update primary key
                setattr(target, c.name, getattr(source, c.name))

    @classmethod
    def get_all(cls, session: Session) -> List[T]:
        """Load all orders from the database.

        Args:
            session: Database session

        Returns:
            Dictionary of orders with ID as key
        """
        return session.query(cls.model).all()  # type: ignore

    @classmethod
    def get_by_id(cls, order_id: str, session: Session) -> Optional[T]:
        """Get an order by its ID.

        Args:
            order_id: The ID of the order to retrieve
            session: Database session

        Returns:
            The order if found, None otherwise
        """
        return session.query(cls.model).filter_by(id=order_id).first()  # type: ignore

    @classmethod
    def get_waiting_orders(cls, session: Session) -> List[T]:
        """Get all active orders.

        Args:
            session: Database session

        Returns:
            List of active orders
        """
        return session.query(cls.model).filter(cls.model.status == CustomOrderStatus.WAITING).all()  # type: ignore

    @classmethod
    def get_by_status(cls, status: CustomOrderStatus, session: Session) -> List[T]:
        """Get all orders with a specific status.

        Args:
            status: The status to filter orders by
            session: Database session

        Returns:
            List of orders with the specified status
        """
        return session.query(cls.model).filter(cls.model.status == status).all()  # type: ignore

    @classmethod
    def delete(cls, order_id: str, session: Session) -> bool:
        """Delete an order by its ID.

        Args:
            order_id: The ID of the order to delete
            session: Database session

        Returns:
            True if the order was deleted, False otherwise
        """
        order = session.query(cls.model).filter_by(id=order_id).first()
        if order:
            session.delete(order)
            session.commit()
            return True
        return False


class RangeBucketBuyOrderRepository(BaseCustomOrderRepository):
    model = RangeBucketBuyOrderModel


class TrailingStopBuyOrderRepository(BaseCustomOrderRepository):
    model = TrailingStopBuyOrderModel


class TrailingStopSellOrderRepository(BaseCustomOrderRepository):
    model = TrailingStopSellOrderModel
