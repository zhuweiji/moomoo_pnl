from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.utilities import DEFAULT_TZ
from src.financial_news.models import (
    FinancialNewsItem,
    FinancialNewsItemModel,
    NewsSourceModel,
)
from src.financial_news.repositories import (
    FinancialNewsItemJsonFileRepository,
    FinancialNewsItemModelRepository,
    NewsSourceRepository,
)


class TestFinancialNewItemJsonFileRepository:
    def setup_method(self):
        self.temp_dir = TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "financial_news.json"
        self.repository = FinancialNewsItemJsonFileRepository(self.storage_path, FinancialNewsItem)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_save_load_single_news_item(self):
        """Test saving and loading a single financial news item."""
        news_item = FinancialNewsItem(
            title="Test News",
            description="Test Description",
            link="https://example.com/news/1",
            source="Test Source",
            published=datetime(2023, 1, 1, 12, 0, tzinfo=DEFAULT_TZ),
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
                published=datetime(2023, 1, 1, 12, 0, tzinfo=DEFAULT_TZ),
            ),
            FinancialNewsItem(
                title="Test News2",
                description="Test Description2",
                link="https://example.com/news/2",
                source="Test Source2",
                published=datetime(2023, 1, 1, 12, 2, tzinfo=DEFAULT_TZ),
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


class TestNewsSourceRepository:
    def test_create_source(self, db_session):
        source = NewsSourceRepository.create(name="Reuters", session=db_session)
        assert source
        assert source.name == "Reuters"
        assert source.id is not None

    def test_get_by_name(self, db_session):
        created_source = NewsSourceRepository.create(name="Reuters", session=db_session)

        retrieved_source = NewsSourceRepository.get_by_name("Reuters", session=db_session)
        assert retrieved_source is not None
        assert retrieved_source.name == created_source.name
        assert retrieved_source.id == created_source.id

    def test_get_by_name_not_found(self, db_session):
        retrieved_source = NewsSourceRepository.get_by_name("NonExistent", session=db_session)
        assert retrieved_source is None

    def test_get_or_create_existing(self, db_session):
        source1 = NewsSourceRepository.create(name="Reuters", session=db_session)
        source2 = NewsSourceRepository.get_or_create(name="Reuters", session=db_session)

        assert source1.id == source2.id
        assert source1.name == source2.name

    def test_get_or_create_new(self, db_session):
        source = NewsSourceRepository.get_or_create(name="Reuters", session=db_session)

        assert source.name == "Reuters"
        assert source.id is not None


class TestFinancialNewsItemModelRepository:
    def test_create_from_model(self, db_session):
        source = NewsSourceRepository.create(name="Reuters", session=db_session)

        news_item = FinancialNewsItemModel(
            title="Test News", description="Test Description", link="https://example.com", source=source, published=datetime.now(tz=DEFAULT_TZ)
        )

        created_item = FinancialNewsItemModelRepository.create_from_model(news_item, session=db_session)

        assert created_item.title == "Test News"
        assert created_item.source.name == "Reuters"
        assert created_item.id is not None

    def test_get_by_source(self, db_session):
        # Create two sources
        reuters = NewsSourceRepository.create(name="Reuters", session=db_session)
        bloomberg = NewsSourceRepository.create(name="Bloomberg", session=db_session)

        # Create news items for each source
        reuters_news = FinancialNewsItemModel(
            title="Reuters News", description="Reuters Description", link="https://reuters.com", source=reuters, published=datetime.now(tz=DEFAULT_TZ)
        )
        bloomberg_news = FinancialNewsItemModel(
            title="Bloomberg News",
            description="Bloomberg Description",
            link="https://bloomberg.com",
            source=bloomberg,
            published=datetime.now(tz=DEFAULT_TZ),
        )

        FinancialNewsItemModelRepository.create_from_model(reuters_news, session=db_session)
        FinancialNewsItemModelRepository.create_from_model(bloomberg_news, session=db_session)

        # Test retrieving by source
        reuters_items = FinancialNewsItemModelRepository.get_by_source("Reuters", session=db_session)
        assert len(reuters_items) == 1
        assert reuters_items[0].title == "Reuters News"
        assert reuters_items[0].source.name == "Reuters"

        bloomberg_items = FinancialNewsItemModelRepository.get_by_source("Bloomberg", session=db_session)
        assert len(bloomberg_items) == 1
        assert bloomberg_items[0].title == "Bloomberg News"
        assert bloomberg_items[0].source.name == "Bloomberg"
