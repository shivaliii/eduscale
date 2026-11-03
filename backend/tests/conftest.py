"""
Pytest configuration and fixtures for EduScale backend tests.

Uses SQLite in-memory database for fast, isolated testing.
Provides fixtures for:
  - Database session
  - FastAPI test client
  - Pre-seeded demo data
  - Authenticated user tokens
"""
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override DATABASE_URL before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DEMO_MODE"] = "true"

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403 — import all models to register them


# ── SQLite test engine ──────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the database dependency for testing."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all database tables once for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def db_session():
    """Provide a transactional database session for each test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def seeded_db(db_session):
    """Seed the database with demo data and return the session."""
    from app.seed.seed_database import seed_database
    seed_database(db_session)
    db_session.commit()
    return db_session


@pytest.fixture
def teacher_token(client, seeded_db):
    """Get a JWT token for the demo teacher."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "teacher@eduscale.demo",
            "password": "teacher123",
        },
    )
    assert response.status_code == 200, f"Teacher login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def student_token(client, seeded_db):
    """Get a JWT token for the demo student (Alex)."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "alex@eduscale.demo",
            "password": "student123",
        },
    )
    assert response.status_code == 200, f"Student login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def auth_headers_teacher(teacher_token):
    """Authorization headers for teacher."""
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest.fixture
def auth_headers_student(student_token):
    """Authorization headers for student."""
    return {"Authorization": f"Bearer {student_token}"}

