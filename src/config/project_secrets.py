from os import environ

import dotenv

from src.config.project_paths import top_level_dir

dotenv.load_dotenv(top_level_dir / ".env")
