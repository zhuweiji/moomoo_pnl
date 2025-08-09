import asyncio
import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Collection, Dict, List, Optional, Set, TypeAlias

import aiohttp
import feedparser
import requests

from src.core.utilities import (
    DEFAULT_TZ,
    EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS,
    EXTERNAL_SERVICE_MAX_CONCURRENT_REQUESTS,
    FINANCIAL_NEWS_JSON_FILEPATH,
    RSS_FEED_REFRESH_INTERVAL_SECONDS,
    RSSFeedSources,
    SingletonThreadedService,
    ThreadedService,
    ThreadSafeTimedCache,
    datetime_from_iso8601,
    datetime_iso8601_str,
    datetime_to_iso8601_str,
    get_logger,
    url,
)
from src.financial_news.repositories import FinancialNewItemJsonFileRepository

from .models import FinancialNewsItem

# Configure logging
log = get_logger(__name__)


class RSSFeedQueryService:
    """Perform queries to RSS Feeds"""

    @classmethod
    def query_feed(cls, url: str) -> tuple[FinancialNewsItem]:
        """Fetch and parse a single RSS feed."""
        response = requests.get(url=url)
        content = response.text
        feed = feedparser.parse(content)

        items = []

        for entry in feed.entries:
            # Extract basic information
            title = getattr(entry, "title", "No title")
            description = getattr(entry, "description", "") or getattr(entry, "summary", "")
            link = getattr(entry, "link", "")

            # Handle publication date
            pub_date_str = getattr(entry, "published", "") or getattr(entry, "updated", "")
            pub_date = datetime_from_iso8601(pub_date_str)

            news_item = FinancialNewsItem(
                title=title,
                description=description,
                link=link,
                published=pub_date,
                source=url,
            )
            items.append(news_item)

        log.info(f"Fetched {len(items)} items from {url}")
        return tuple(items)


class FinancialRSSDataService(SingletonThreadedService):
    """Provides consolidated access to all feeds registered in the app with built-in caching.

    Multiple instances of the service can be created and can attempt to fetch data from RSS feeds,
    but data will be retrieved from cache if there is recent data available.

    Periodically queries the feeds to keep the data up to date


    On startup: refreshes cache with old data from repository
    Every query_interval_seconds seconds, queries for new da
    """

    data: set[FinancialNewsItem] = set()
    repository = FinancialNewItemJsonFileRepository(storage_path=FINANCIAL_NEWS_JSON_FILEPATH, item_class=FinancialNewsItem)

    rss_feed_service = RSSFeedQueryService

    def __init__(
        self,
        query_interval_seconds: int = RSS_FEED_REFRESH_INTERVAL_SECONDS,
        max_concurrent_requests: int = EXTERNAL_SERVICE_MAX_CONCURRENT_REQUESTS,
        timeout: int = EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS,
    ):
        super().__init__(check_interval_seconds=query_interval_seconds)

        # config
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout
        self.rss_feeds: dict[str, url] = {source.name: source.value for source in RSSFeedSources}

    def start(self):
        super().start()
        self.data.update(self.repository.get_all())

    def add_source(self, name: str, url: url):
        """Add a new RSS source."""
        self.rss_feeds[name] = url

    def remove_source_by_name(self, name: str):
        """Remove an RSS source."""
        if name in self.rss_feeds:
            del self.rss_feeds[name]

    def get_sources(self) -> dict[str, url]:
        """Get list of available news sources."""
        return self.rss_feeds

    def run(self):
        """Refreshes the data from its sources"""
        self._update_all_feeds()

    def _update_all_feeds(self):
        """Fetch all RSS feeds"""
        for rss_feed_url in self.rss_feeds.values():
            try:
                self.data.update(self.rss_feed_service.query_feed(url=rss_feed_url))
            except Exception as e:
                log.error(e)

        self.repository.save_all(self.data)

    def get_news(
        self,
        url_filter: Optional[Collection[str]] = None,
        symbol_filter: Optional[List[str]] = None,
        source_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
        hours_back: Optional[int] = 24,
    ):
        return self.data


if __name__ == "__main__":
    s = FinancialRSSDataService(query_interval_seconds=60 * 10)
    s.start()

    print(s.get_news())
