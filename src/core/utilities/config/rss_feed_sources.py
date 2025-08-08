from enum import Enum


class RSSFeedSources(Enum):
    YAHOO_FINANCE = "https://feeds.finance.yahoo.com/rss/2.0/headline"
    MARKETWATCH = "https://feeds.marketwatch.com/marketwatch/topstories/"
    REUTERS_FINANCIAL = "https://ir.thomsonreuters.com/rss/news-releases.xml?items=100"
    REUTERS_CALENDAR = "https://ir.thomsonreuters.com/rss/events.xml?items=100"
    REUTERS_SEC_NEWS = "https://ir.thomsonreuters.com/rss/sec-filings.xml?items=100"
    SEEKING_ALPHA = "https://seekingalpha.com/feed.xml"
    ZACKS = "https://www.zacks.com/rss/rss_news.php"
    FINVIZ = "https://finviz.com/news.ashx?v=3"
    CNBC = "https://feeds.feedburner.com/cnbc/business"
