"""
Shared test fixtures for Moonjar PMS.
"""
import pytest
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from api.database import Base, get_db
from api.config import settings


# Test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.split("/")[-1], "moonjar_test"
) if settings.DATABASE_URL else "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(db_engine):
    """Get test database session with rollback."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """Get test HTTP client with DB override."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Get auth headers for test requests."""
    # TODO: generate test JWT token
    return {"Cookie": "access_token=test_token"}


@pytest.fixture
def sample_factory(db):
    """Create a sample factory for tests."""
    # TODO: create and return factory model instance
    pass


@pytest.fixture
def sample_user(db, sample_factory):
    """Create a sample user for tests."""
    # TODO: create and return user model instance
    pass


@pytest.fixture
def sample_order(db, sample_factory):
    """Create a sample order with positions for tests."""
    # TODO: create and return order + positions
    pass
