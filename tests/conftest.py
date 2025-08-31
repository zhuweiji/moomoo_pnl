import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    # BaseModel.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
