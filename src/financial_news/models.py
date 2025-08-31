from datetime import datetime

import pydantic
from pydantic import ConfigDict
from sqlalchemy import JSON, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column, relationship

from src.core.database import BaseModel, SessionMaker, engine
from src.core.database.custom_types import TZDateTime
from src.core.utilities import DEFAULT_TZ, get_logger, url

log = get_logger(__name__)


class FinancialNewsItem(pydantic.BaseModel, frozen=True):
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
        if "published" in data and isinstance(data["published"], str):
            data["published"] = datetime.fromisoformat(data["published"])

        if not data["published"].tzinfo:
            data["published"] = data["published"].astimezone(tz=DEFAULT_TZ)

        return cls(**data)


class NewsSourceModel(BaseModel):
    __tablename__ = "news_sources"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String, unique=True, nullable=False)

    # relationships
    news_items = relationship("FinancialNewsItemModel", back_populates="source")


class FinancialNewsItemModel(BaseModel):
    __tablename__ = "financial_news"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String)
    description = mapped_column(String)
    link = mapped_column(String)
    source_id = mapped_column(Integer, ForeignKey("news_sources.id"), nullable=False)
    published = mapped_column(TZDateTime, nullable=True)

    # Relationships
    source = relationship("NewsSourceModel", back_populates="news_items")

    @classmethod
    def from_dataclass(cls, item: FinancialNewsItem) -> "FinancialNewsItemModel":
        from src.financial_news.repositories import NewsSourceRepository

        source = NewsSourceRepository.get_or_create(name=item.source, session=NewsSourceRepository.get_db_session())

        return cls(
            title=item.title,
            description=item.description,
            link=item.link,
            source=source,
            published=item.published,
        )

    def to_dataclass(self):
        return FinancialNewsItem(
            title=str(self.title),
            description=str(self.description),
            link=str(self.link),
            source=str(self.source.name),
            published=self.published,  # type: ignore
        )
