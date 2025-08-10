from pathlib import Path

TOP_LEVEL_DIR = Path(__file__).parents[4]
DATA_DIR = TOP_LEVEL_DIR / "data"

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_DATABASE_FILEPATH = DATA_DIR / "dev.db"
SQLITE_DATABASE_URI = f"sqlite:///{SQLITE_DATABASE_FILEPATH}"
SQLITE_TEST_DATABASE_URI = "sqlite:///test.db"

FINANCIAL_NEWS_JSON_FILEPATH = DATA_DIR / "financial_news.json"
STRUCTURED_TEXT_DATA_DIR = DATA_DIR / "structured_text_data"

EXTRACTION_RESULT_DIR = STRUCTURED_TEXT_DATA_DIR / "extraction_data"
EXTRACTION_VISUALIZATION_DIR = STRUCTURED_TEXT_DATA_DIR / "extraction_viz"

if not EXTRACTION_RESULT_DIR.exists():
    EXTRACTION_RESULT_DIR.mkdir(parents=True, exist_ok=True)

if not EXTRACTION_VISUALIZATION_DIR.exists():
    EXTRACTION_VISUALIZATION_DIR.mkdir(parents=True, exist_ok=True)
