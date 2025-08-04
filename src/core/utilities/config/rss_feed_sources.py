from enum import Enum


class RSSFeedSources(Enum):
    YAHOO_FINANCE = "https://feeds.finance.yahoo.com/rss/2.0/headline"
    MARKETWATCH = "https://feeds.marketwatch.com/marketwatch/topstories/"
    REUTERS_BUSINESS = "https://feeds.reuters.com/reuters/businessNews"
    SEEKING_ALPHA = "https://seekingalpha.com/feed.xml"
    BENZINGA = "https://feeds.benzinga.com/benzinga"
    ZACKS = "https://www.zacks.com/rss/rss_news.php"
    FINVIZ = "https://finviz.com/news.ashx?v=3"
    CNBC = "https://feeds.feedburner.com/cnbc/business"
