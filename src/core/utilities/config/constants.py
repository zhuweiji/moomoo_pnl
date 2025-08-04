import os

import pytz

# populate env vars from .env
from .project_secrets import *
from .rss_feed_sources import *

# this stuff is stored in envvars until there's enough of them that making a top-level config.yml makes sense
SITE_PORT = int(os.environ["SITE_PORT"])
NTFY_SH_TOPIC = os.environ["NTFY_SH_TOPIC"]

MOOMOO_FIRST_ORDER_DATE = "2024-03-31 00:00:00"

DEFAULT_TZ = pytz.utc

EXTERNAL_SERVICE_MAX_CONCURRENT_REQUESTS = 10
EXTERNAL_SERVICE_DEFAULT_TIMEOUT_SECONDS = 60
RSS_FEED_REFRESH_INTERVAL_SECONDS = 60 * 60 * 6  # 6 hours

INTERNAL_THREADED_SERVICE_RUN_SECONDS = 5
