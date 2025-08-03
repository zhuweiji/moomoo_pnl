import os

import pytz

# populate env vars from .env
from .project_secrets import *

# this stuff is stored in envvars until there's enough of them that making a top-level config.yml makes sense
SITE_PORT = int(os.environ["SITE_PORT"])
NTFY_SH_TOPIC = os.environ["NTFY_SH_TOPIC"]

MOOMOO_FIRST_ORDER_DATE = "2024-03-31 00:00:00"

DEFAULT_TZ = pytz.utc

EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS = 60
RSS_FEED_REFRESH_INTERVAL_SECONDS = 60 * 60 * 6  # 6 hours

INTERNAL_THREADED_SERVICE_RUN_SECONDS = 5

# Financial RSS feeds - mix of free and commonly available sources
RSS_FEED_MAP: dict[str, str] = {
    "yahoo_finance": "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "seeking_alpha": "https://seekingalpha.com/feed.xml",
    "benzinga": "https://feeds.benzinga.com/benzinga",
    "zacks": "https://www.zacks.com/rss/rss_news.php",
    "finviz": "https://finviz.com/news.ashx?v=3",
    "cnbc": "https://feeds.feedburner.com/cnbc/business",
}
