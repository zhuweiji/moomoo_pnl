from pathlib import Path

TOP_LEVEL_DIR = Path(__file__).parents[4]
DATA_DIR = TOP_LEVEL_DIR / "data"

FINANCIAL_NEWS_JSON_FILEPATH = DATA_DIR / "financial_news.json"
