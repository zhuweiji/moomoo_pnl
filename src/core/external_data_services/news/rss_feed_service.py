import asyncio
import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import aiohttp
import feedparser

from src.core.utilities import (
    EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS,
    RSS_FEED_MAP,
    RSS_FEED_REFRESH_INTERVAL_SECONDS,
    Singleton,
    ThreadedService,
    get_logger,
)

# Configure logging
log = get_logger(__name__)


@dataclass
class FinancialNewsItem:
    """Represents a single news item from an RSS feed."""

    title: str
    description: str
    link: str
    source: str
    guid: str
    hash_id: str  # Unique identifier

    published: datetime | None = None
    tags: list[str] | None = None
    symbols: list[str] | None = None
    sentiment_keywords: list[str] | None = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SingleRSSFeedService:
    timeout_seconds: int = EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS

    async def fetch_feed(self, session: aiohttp.ClientSession, name: str, url: str) -> List[FinancialNewsItem]:
        """Fetch and parse a single RSS feed."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)) as response:
                content = await response.text()
                feed = feedparser.parse(content)

                items = []

                for entry in feed.entries:
                    # Extract basic information
                    title = getattr(entry, "title", "No title")
                    description = getattr(entry, "description", "") or getattr(entry, "summary", "")
                    link = getattr(entry, "link", "")

                    # Handle publication date
                    # pub_date = getattr(entry, "published", "") or getattr(entry, "updated", "")
                    # if hasattr(entry, "published_parsed") and entry.published_parsed:
                    #     pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                    pub_date = None

                    # Create unique identifier
                    guid = getattr(entry, "id", "") or link
                    hash_id = hashlib.md5(f"{title}{link}{pub_date}".encode()).hexdigest()

                    news_item = FinancialNewsItem(
                        title=title,
                        description=description,
                        link=link,
                        published=pub_date,
                        source=name,
                        guid=guid,
                        hash_id=hash_id,
                    )
                    items.append(news_item)

                log.info(f"Fetched {len(items)} items from {name}")
                return items

        except Exception as e:
            log.error(f"Error fetching {name}: {str(e)}")
            return []


class FinancialRSSService(ThreadedService):
    """
    A comprehensive RSS feed service for financial news aggregation.
    Designed for AI agentic systems and programmatic access.
    """

    __metaclass__ = Singleton  # make all API calls from a Singleton object so we don't accidentally spam services if we create multiple instances

    def __init__(
        self,
        max_concurrent_requests: int = 10,
        timeout: int = 30,
    ):
        super().__init__(check_interval_seconds=RSS_FEED_REFRESH_INTERVAL_SECONDS)

        # config
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.rss_feeds = RSS_FEED_MAP

        # services
        self.rss_feed_service = SingleRSSFeedService()

        # internals
        self.last_fetch = {}

    def add_source(self, name: str, url: str):
        """Add a new RSS source."""
        self.rss_feeds[name] = url
        log.info(f"Added new source: {name}")

    def remove_source(self, name: str):
        """Remove an RSS source."""
        if name in self.rss_feeds:
            del self.rss_feeds[name]
            log.info(f"Removed source: {name}")

    def get_sources(self) -> List[str]:
        """Get list of available news sources."""
        return list(self.rss_feeds.keys())

    async def run(self):
        """Refreshes the data from its sources"""

        # Check cache first
        log.info("Fetching fresh news data")
        news_items = await self._fetch_all_feeds()
        self.last_fetch["timestamp"] = time.time()

        return [item.to_dict() for item in news_items]

    async def _fetch_all_feeds(self) -> List[FinancialNewsItem]:
        """Fetch all RSS feeds concurrently."""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent_requests)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for name, url in self.rss_feeds.items():
                task = self.rss_feed_service.fetch_feed(session, name, url)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_items = []
            for result in results:
                if isinstance(result, list):
                    all_items.extend(result)
                else:
                    log.error(f"Task failed: {result}")

            return all_items

    async def get_news(
        self,
        symbol_filter: Optional[List[str]] = None,
        source_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
        hours_back: Optional[int] = 24,
    ):
        pass
