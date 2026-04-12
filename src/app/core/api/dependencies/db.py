from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import AsyncGenerator

from app.core.config.database import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session