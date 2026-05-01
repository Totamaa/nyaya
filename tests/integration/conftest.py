import pytest

from app.modules.base.model import BaseModel


@pytest.fixture(autouse=True)
async def clean_db(db_session):
    yield
    await db_session.rollback()
    for table in reversed(BaseModel.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()
