import asyncio

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config.settings import get_settings

import app.modules.users.model  # noqa: F401
import app.modules.messages.model  # noqa: F401
import app.modules.evaluations.model  # noqa: F401
import app.modules.totems.model  # noqa: F401
import app.modules.user_totems.model  # noqa: F401
import app.modules.feedbacks.model  # noqa: F401


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def test_db_name(settings) -> str:
    return f"{settings.DB_NAME}_test"


@pytest.fixture(scope="session")
def test_db_url(settings, test_db_name) -> str:
    return (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{test_db_name}"
    )


@pytest.fixture(scope="session", autouse=True)
async def _bootstrap_test_db(settings, test_db_name, test_db_url):
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database="postgres",
    )
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", test_db_name
    )
    if not exists:
        await conn.execute(f'CREATE DATABASE "{test_db_name}"')
    await conn.close()

    def _run_migrations() -> None:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
        command.upgrade(alembic_cfg, "head")

    # Run in a thread: command.upgrade() calls asyncio.run() internally,
    # which cannot nest inside pytest-asyncio's already-running event loop.
    await asyncio.to_thread(_run_migrations)

    yield  # tests run here

    # Drop the test DB entirely after the session.
    # test_engine.dispose() runs before this (reverse dependency order).
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database="postgres",
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)')
    await conn.close()


@pytest.fixture(scope="session")
async def test_engine(test_db_url, _bootstrap_test_db):
    engine = create_async_engine(test_db_url, echo=False)
    yield engine
    await engine.dispose()  # runs before _bootstrap_test_db drops the DB


@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()  # undoes all flushes — test isolation
