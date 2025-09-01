from sqlalchemy.orm import Session

from src.core.database.get_engine import SessionMaker


class BaseRepository:
    @classmethod
    def get_db_session(cls) -> Session:
        """Get the current database session.

        Returns:
            The current SQLAlchemy Session
        """
        return SessionMaker()
