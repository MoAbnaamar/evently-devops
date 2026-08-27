from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import get_store
from app.main import create_app
from app.store import InMemoryStore


# Fresh isolated store instance for each test
@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


# Test client backed by a fresh store instance for each test
@pytest.fixture
def client(store: InMemoryStore) -> Iterator[TestClient]:
    app = create_app()
    
    # Override store dependency to share the same instance across requests
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as test_client:
        yield test_client