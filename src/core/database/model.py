from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .get_engine import Base


class BaseModel(Base):
    __abstract__ = True
    created: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
