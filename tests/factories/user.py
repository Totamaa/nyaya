from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.model import UserModel

fake = Faker()


class UserFactory:
    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> UserModel:
        user = UserModel(external_id=kwargs.get("external_id", str(fake.uuid4())))
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    def build(**kwargs) -> UserModel:
        return UserModel(external_id=kwargs.get("external_id", str(fake.uuid4())))
