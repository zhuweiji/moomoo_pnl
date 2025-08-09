from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.core.utilities import url


class FinancialNewsItem(BaseModel, frozen=True):
    """Represents a single news item from an RSS feed using Pydantic BaseModel."""

    model_config = ConfigDict(extra="ignore")

    title: str
    description: str
    link: url
    source: str
    published: datetime | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
