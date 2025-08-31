import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.database import BaseRepository
from src.core.orders.models2 import BaseModel


def test_db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    TestSessionLocal = sessionmaker(bind=engine)
    BaseModel.metadata.create_all(bind=engine)
    session = TestSessionLocal()

    return session


@pytest.fixture
def db_session():
    """Provides a clean database session for each test."""
    session = test_db_session()
    yield session
    session.close()
