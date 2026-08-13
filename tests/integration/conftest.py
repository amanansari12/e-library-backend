from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import get_db
import app.models  # noqa: F401 - registers all ORM tables on Base.metadata
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    settings = get_settings()
    if settings.test_database_url == settings.database_url:
        raise RuntimeError("TEST_DATABASE_URL must be different from DATABASE_URL")

    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(test_engine):
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client(session_factory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter._storage.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter._storage.reset()
