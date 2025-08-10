from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

from src.core.utilities import get_logger, SQLITE_DATABASE_URI

log = get_logger(__name__)

engine = create_engine(SQLITE_DATABASE_URI)

Base = declarative_base()

SessionMaker = sessionmaker(bind=engine)
