import dotenv

from .project_paths import TOP_LEVEL_DIR

print(f"loading dotenv {TOP_LEVEL_DIR / '.env'}")
dotenv.load_dotenv(TOP_LEVEL_DIR / ".env")
