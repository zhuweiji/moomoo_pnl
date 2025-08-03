class BaseCustomOrder(ABC, Base):
    """Base class for all custom stock orders."""

    __tablename__ = "custom_orders"

    # Primary key
    id = Column(String(50), primary_key=True)

    # Polymorphic identity for inheritance
    order_type = Column(String(50))
    __mapper_args__ = {"polymorphic_identity": "base", "polymorphic_on": order_type, "with_polymorphic": "*"}

    # Core order fields
    stock_code = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)

    # Status and timing
    status = Column(SQLEnum(CustomOrderStatus), default=CustomOrderStatus.WAITING, nullable=False, index=True)
    created_at = Column(TZDateTime, default=datetime.now, nullable=False)
    updated_at = Column(TZDateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Tracking fields
    last_checked_price = Column(Integer)
    last_check_time = Column(DateTime)

    # Error handling and notes
    error_message = Column(Text)
    comments = Column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_common_params(self.quantity)

    @classmethod
    def _validate_common_params(cls, quantity: int) -> None:
        """Validate common parameters for all order types."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

    @abstractmethod
    def get_trigger_price(self) -> Optional[int]:
        """Calculate the price that would trigger this order."""
        pass

    @abstractmethod
    def should_trigger(self, current_price: int) -> bool:
        """Check if the order should be triggered based on current price."""
        pass


class TriggeredBucket(Base):
    """Track which buckets have been triggered for RangeBucketOrder."""

    __tablename__ = "triggered_buckets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("range_bucket_orders.id"), nullable=False)
    bucket_price = Column(Float, nullable=False)
    triggered_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationship back to the order
    order = relationship("RangeBucketOrder", back_populates="triggered_bucket_records")


class RangeBucketOrder(BaseCustomOrder):
    """
    A custom order that buys across a range of prices divided into buckets.
    Either specify num_buckets or bucket_size, but not both.
    """

    __tablename__ = "range_bucket_orders"

    # Foreign key to base table
    id = Column(String(50), ForeignKey("custom_orders.id"), primary_key=True)

    # Range bucket specific fields
    start_price = Column(Float, nullable=False)
    end_price = Column(Float, nullable=False)
    num_buckets = Column(Integer)
    bucket_size = Column(Float)

    # Store buckets as JSON for quick access
    buckets_json = Column(JSON, nullable=False)

    # Polymorphic identity
    __mapper_args__ = {
        "polymorphic_identity": "range_bucket",
    }

    # Relationship to triggered buckets
    triggered_bucket_records = relationship("TriggeredBucket", back_populates="order", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        # Extract buckets-related params before calling super
        start_price = kwargs.get("start_price")
        end_price = kwargs.get("end_price")
        num_buckets = kwargs.get("num_buckets")
        bucket_size = kwargs.get("bucket_size")

        # Validate bucket parameters
        if start_price and end_price:
            if start_price >= end_price:
                raise ValueError("start_price must be less than end_price")

        if num_buckets and bucket_size:
            raise ValueError("Specify only one: num_buckets or bucket_size")

        if not num_buckets and not bucket_size:
            raise ValueError("Must specify either num_buckets or bucket_size")

        # Generate buckets and store as JSON
        if start_price and end_price and (num_buckets or bucket_size):
            buckets = self._generate_buckets_static(start_price, end_price, num_buckets, bucket_size)
            kwargs["buckets_json"] = buckets

        super().__init__(**kwargs)

    @staticmethod
    def _generate_buckets_static(start_price: float, end_price: float, num_buckets: Optional[int], bucket_size: Optional[float]) -> List[float]:
        """Generate the list of bucket prices (static method for use in __init__)."""
        if num_buckets:
            step = (end_price - start_price) / (num_buckets - 1)
            return [round(start_price + i * step, 4) for i in range(num_buckets)]
        else:
            assert bucket_size
            num_buckets_calc = math.floor((end_price - start_price) / bucket_size) + 1
            return [round(start_price + i * bucket_size, 4) for i in range(num_buckets_calc) if start_price + i * bucket_size <= end_price + 1e-8]

    @hybrid_property
    def buckets(self) -> List[float]:
        """Get the list of all bucket prices."""
        return self.buckets_json if self.buckets_json else []

    @hybrid_property
    def triggered_buckets(self) -> List[float]:
        """Get list of triggered bucket prices."""
        return [record.bucket_price for record in self.triggered_bucket_records]

    def get_trigger_price(self) -> Optional[float]:
        """Return the next untriggered bucket price that should trigger."""
        triggered_prices = set(self.triggered_buckets)
        for price in self.buckets:
            if price not in triggered_prices:
                return price
        return None  # All buckets triggered

    def should_trigger(self, current_price: float) -> bool:
        """Check if current price matches an untriggered bucket."""
        # Use some tolerance because of float precision issues
        tolerance = 1e-4
        triggered_prices = set(self.triggered_buckets)

        for price in self.buckets:
            if price not in triggered_prices:
                if abs(current_price - price) <= tolerance:
                    return True
        return False

    def mark_bucket_triggered(self, price: float, session):
        """
        Mark a bucket price as triggered (after placing order).
        Requires SQLAlchemy session to persist the triggered bucket.
        """
        triggered_prices = set(self.triggered_buckets)

        if price in self.buckets and price not in triggered_prices:
            # Create new triggered bucket record
            triggered_bucket = TriggeredBucket(order_id=self.id, bucket_price=price)
            session.add(triggered_bucket)

            # Update the order timestamp
            self.updated_at = datetime.now()

            # Check if all buckets are now triggered
            if len(self.triggered_buckets) + 1 == len(self.buckets):  # +1 for the one we just added
                self.status = CustomOrderStatus.COMPLETED

    def remaining_buckets(self) -> List[float]:
        """Get list of remaining bucket prices not yet triggered."""
        triggered_prices = set(self.triggered_buckets)
        return [price for price in self.buckets if price not in triggered_prices]

    @hybrid_property
    def total_price_estimate(self) -> float:
        """Utility property: estimate total price of order if all buckets trigger."""
        if not self.buckets:
            return 0.0

        # Simple estimation: average bucket price * quantity * number of buckets
        avg_price = sum(self.buckets) / len(self.buckets)
        return avg_price * self.quantity * len(self.buckets)
