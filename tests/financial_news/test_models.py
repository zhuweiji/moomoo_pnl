from datetime import datetime

import pytest

from src.core.utilities import DEFAULT_TZ
from src.financial_news.models import FinancialNewsItem, FinancialNewsItemModel, NewsSourceModel


def test_financial_news_item_creation():
    news_item = FinancialNewsItem(
        title="Test News",
        description="Test Description",
        link="https://example.com",
        source="Reuters",
        published=datetime(2023, 1, 1, 12, 0, tzinfo=DEFAULT_TZ),
    )

    assert news_item.title == "Test News"
    assert news_item.description == "Test Description"
    assert news_item.link == "https://example.com"
    assert news_item.source == "Reuters"
    assert news_item.published == datetime(2023, 1, 1, 12, 0, tzinfo=DEFAULT_TZ)


def test_financial_news_item_to_dict():
    news_item = FinancialNewsItem(
        title="Test News",
        description="Test Description",
        link="https://example.com",
        source="Reuters",
        published=datetime(2023, 1, 1, 12, 0, tzinfo=DEFAULT_TZ),
    )

    data = news_item.to_dict()
    assert isinstance(data, dict)
    assert data["title"] == "Test News"
    assert data["source"] == "Reuters"


def test_financial_news_item_from_dict():
    data = {
        "title": "Test News",
        "description": "Test Description",
        "link": "https://example.com",
        "source": "Reuters",
        "published": "2023-01-01T12:00:00",
    }

    news_item = FinancialNewsItem.from_dict(data)
    assert news_item.title == "Test News"
    assert news_item.source == "Reuters"


def test_financial_news_item_model_conversion():
    # Create a source
    source = NewsSourceModel(name="Reuters")

    # Create a news item
    news_item = FinancialNewsItem(
        title="Test News",
        description="Test Description",
        link="https://example.com",
        source="Reuters",
        published=datetime(2023, 1, 1, 12, 0, tzinfo=DEFAULT_TZ),
    )

    # Convert to model
    model = FinancialNewsItemModel.from_dataclass(news_item)
    model.source = source

    # Convert back to dataclass
    converted = model.to_dataclass()

    assert converted.title == news_item.title
    assert converted.description == news_item.description
    assert converted.link == news_item.link
    assert converted.source == news_item.source
    assert converted.published == news_item.published
