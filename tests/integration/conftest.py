from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.api.dependencies.auth import verify_api_key
from app.core.api.dependencies.db import get_session
from app.modules.base.model import BaseModel


@pytest.fixture(autouse=True)
async def clean_db(db_session):
    yield
    await db_session.rollback()
    for table in reversed(BaseModel.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()


@pytest.fixture
def _test_app(db_session):
    from app.main import create_app

    app = create_app()

    async def override_session():
        yield db_session

    async def override_auth():
        return None

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[verify_api_key] = override_auth
    return app


@pytest.fixture
async def client(_test_app):
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as c:
            yield c


@pytest.fixture
async def authed_client(_test_app, settings):
    """Client with a real API key — for auth-specific tests."""
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app),
            base_url="http://test",
            headers={"X-API-Key": settings.API_KEY},
        ) as c:
            yield c
