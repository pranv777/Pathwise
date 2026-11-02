import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.db import Base, get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.security import create_access_token
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    db = TestSessionLocal()
    yield db
    db.rollback()
    # Explicitly wipe rows created during the test — a plain rollback()
    # doesn't undo a transaction that was already committed.
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


@pytest.fixture()
def test_user(db_session):
    import uuid

    unique = uuid.uuid4().hex[:8]
    user = User(
        google_id=f"test-{unique}",
        email=f"test-{unique}@example.com",
        name="Test User",
        picture=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(test_user):
    token = create_access_token(test_user.id, test_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(db_session, test_user):
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The suite makes many requests from one 'IP'; don't let slowapi throttle it."""
    from app.rate_limit import limiter

    limiter.reset()
    yield


@pytest.fixture()
def other_user(db_session):
    import uuid

    unique = uuid.uuid4().hex[:8]
    user = User(
        google_id=f"other-{unique}",
        email=f"other-{unique}@example.com",
        name="Other User",
        picture=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def as_user(client):
    """Switch the authenticated user mid-test: `as_user(other_user)`."""

    def _switch(user):
        app.dependency_overrides[get_current_user] = lambda: user

    return _switch
