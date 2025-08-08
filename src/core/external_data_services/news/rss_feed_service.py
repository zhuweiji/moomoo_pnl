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
    RSS_FEED_REFRESH_INTERVAL_SECONDS,
    RSSFeedSources,
    ThreadedService,
    ThreadSafeTimedCache,
    datetime_iso8601_str,
    datetime_to_iso8601_str,
    get_logger,
)

# Configure logging
log = get_logger(__name__)

url: TypeAlias = str


@dataclass(eq=True, frozen=True)
class FinancialNewsItem:
    """Represents a single news item from an RSS feed."""

    title: str
    description: str
    link: str
    source: url
    hash_id: str  # Unique identifier
    published: datetime | None = None

    def to_dict(self) -> Dict:
        return asdict(self)


class RSSFeedQueryService:
    """Perform queries to RSS Feeds with built-in caching.

    Multiple instances of the service can be created and can attempt to fetch data from RSS feeds,
    but data will be retrieved from cache if there is recent data available.
    """

    cache = ThreadSafeTimedCache[url, tuple[FinancialNewsItem]]()

    def __init__(self, stale_after: timedelta) -> None:
        self.query_interval = stale_after

    def get_all_previous_data_from_feed(self, url: url):
        previous_data_with_fetched_timestamps = self.cache.get_all_from_key(url)
        if not previous_data_with_fetched_timestamps:
            return []

        data: Collection[FinancialNewsItem] = []
        for feed_data in previous_data_with_fetched_timestamps:
            news_items, fetched_timestamp = feed_data
            data.extend(news_items)
        return data

    def query_feed(self, url: str):
        return self.cache.get_or_fetch(key=url, fetch_func=lambda: self._query_feed(url), max_age=self.query_interval)

    @classmethod
    def _query_feed(cls, url: str) -> tuple[FinancialNewsItem]:
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
            # pub_date = getattr(entry, "published", "") or getattr(entry, "updated", "")
            pub_date = None

            # Create unique identifier
            hash_id = hashlib.md5(f"{title}{link}{pub_date}".encode()).hexdigest()

            news_item = FinancialNewsItem(
                title=title,
                description=description,
                link=link,
                published=pub_date,
                source=url,
                hash_id=hash_id,
            )
            items.append(news_item)

        log.info(f"Fetched {len(items)} items from {url}")
        return tuple(items)


class FinancialRSSDataService(ThreadedService):
    """Provides consolidated access to all feeds registered in the app

    Periodically queries the feeds to keep the data up to date"""

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

        self.rss_feed_service = RSSFeedQueryService(stale_after=timedelta(seconds=query_interval_seconds - 1))

        # internals
        self.data: dict[url, Collection[FinancialNewsItem]] = {}

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
        self._fetch_all_feeds()

    def _fetch_all_feeds(self) -> list[FinancialNewsItem]:
        """Fetch all RSS feeds"""
        result = []
        for rss_feed_url in self.rss_feeds.values():
            try:
                result.extend(self.rss_feed_service.query_feed(url=rss_feed_url))
            except Exception as e:
                log.error(e)
        return result

    def get_news(
        self,
        url_filter: Optional[Collection[str]] = None,
        symbol_filter: Optional[List[str]] = None,
        source_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
        hours_back: Optional[int] = 24,
    ):
        result: Collection[FinancialNewsItem] = []
        for rss_feed_url in self.rss_feeds.values():
            result.extend(self.rss_feed_service.get_all_previous_data_from_feed(rss_feed_url))
        return result


if __name__ == "__main__":
    s = FinancialRSSDataService(query_interval_seconds=60 * 10)
    # start the service, which makes it poll for new data every query_interval_seconds
    s.start()

    # get all the news that we collected
    print(s.get_news())
