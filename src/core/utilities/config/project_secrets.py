import dotenv

from .project_paths import top_level_dir

print(f"loading dotenv {top_level_dir / '.env'}")
dotenv.load_dotenv(top_level_dir / ".env")
