import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import aiohttp
import feedparser

from src.core.utilities import (
    EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS,
    RSS_CACHE_DURATION_SECONDS,
    RSS_FEED_MAP,
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


class FinancialRSSService:
    """
    A comprehensive RSS feed service for financial news aggregation.
    Designed for AI agentic systems and programmatic access.
    """

    def __init__(
        self,
        cache_duration: int = RSS_CACHE_DURATION_SECONDS,  # 5 minutes
        max_concurrent_requests: int = 10,
        timeout: int = 30,
    ):
        self.cache_duration = cache_duration
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout = timeout

        self.rss_feeds = RSS_FEED_MAP

        self.rss_feed_service = SingleRSSFeedService()

        # internals
        self.cache = {}
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

    def _should_fetch(self) -> bool:
        """Check if we should fetch new data based on cache duration."""
        if not self.last_fetch:
            return True
        return time.time() - self.last_fetch.get("timestamp", 0) > self.cache_duration

    async def get_news(
        self,
        symbol_filter: Optional[List[str]] = None,
        source_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
        hours_back: Optional[int] = 24,
    ) -> List[Dict]:
        """
        Get financial news with optional filtering.

        Args:
            symbol_filter: Filter by stock symbols
            source_filter: Filter by news sources
            limit: Maximum number of items to return
            hours_back: Only return news from this many hours back

        Returns:
            List of news items as dictionaries
        """
        # Check cache first
        if self._should_fetch():
            log.info("Fetching fresh news data")
            news_items = await self._fetch_all_feeds()
            self.cache["news"] = news_items
            self.last_fetch["timestamp"] = time.time()
        else:
            log.info("Using cached news data")
            news_items = self.cache.get("news", [])

        return [item.to_dict() for item in news_items]
