from sqlalchemy.ext.declarative import declarative_base

from src.core.utilities.logger import get_logger

log = get_logger(__name__)

Base = declarative_base()
