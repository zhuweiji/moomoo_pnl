from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    __abstract__ = True
    created_on: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_on: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
