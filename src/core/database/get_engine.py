from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.utilities import SQLITE_DATABASE_URI, get_logger

log = get_logger(__name__)

engine = create_engine(SQLITE_DATABASE_URI)


SessionMaker = sessionmaker(bind=engine)
