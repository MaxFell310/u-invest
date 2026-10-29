from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from u_invest.database import create_database_engine
from u_invest.main import create_app
from u_invest.models import Base


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    app = create_app(engine)
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
