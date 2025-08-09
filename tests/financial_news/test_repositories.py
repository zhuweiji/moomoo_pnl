from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.financial_news.models import FinancialNewsItem
from src.financial_news.repositories import FinancialNewItemJsonFileRepository


class TestFinancialNewItemJsonFileRepository:
    def setup_method(self):
        self.temp_dir = TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "financial_news.json"
        self.repository = FinancialNewItemJsonFileRepository(self.storage_path, FinancialNewsItem)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_save_load_single_news_item(self):
        """Test saving and loading a single financial news item."""
        news_item = FinancialNewsItem(
            title="Test News",
            description="Test Description",
            link="https://example.com/news/1",
            source="Test Source",
            published=datetime(2023, 1, 1, 12, 0),
        )

        # Save single item
        self.repository.save_all([news_item])

        # Load and verify
        loaded_items = self.repository.get_all()

        assert len(loaded_items) == 1
        loaded_item = loaded_items[0]
        assert loaded_item.title == news_item.title
        assert loaded_item.description == news_item.description
        assert loaded_item.link == news_item.link
        assert loaded_item.source == news_item.source
        assert loaded_item.published == news_item.published

    def test_save_load_multiple_news_items(self):
        """Test saving and loading a single financial news item."""
        news_items = [
            FinancialNewsItem(
                title="Test News",
                description="Test Description",
                link="https://example.com/news/1",
                source="Test Source",
                published=datetime(2023, 1, 1, 12, 0),
            ),
            FinancialNewsItem(
                title="Test News2",
                description="Test Description2",
                link="https://example.com/news/2",
                source="Test Source2",
                published=datetime(2023, 1, 1, 12, 2),
            ),
        ]

        # Save single item
        self.repository.save_all(news_items)

        # Load and verify
        loaded_items = self.repository.get_all()

        assert len(loaded_items) == 2
        for i, loaded_item in enumerate(loaded_items):
            assert loaded_item.title == news_items[i].title
            assert loaded_item.description == news_items[i].description
            assert loaded_item.link == news_items[i].link
            assert loaded_item.source == news_items[i].source
            assert loaded_item.published == news_items[i].published
