import pytest

from app.modules.users.repository import UserRepository
from tests.factories import UserFactory


@pytest.mark.integration
class TestUserRepository:

    async def test_create_and_get_by_id(self, db_session):
        user = await UserFactory.create(db_session)

        repo = UserRepository()
        found = await repo.get_by_id(user_id=user.id, db=db_session)

        assert found is not None
        assert found.id == user.id
        assert found.external_id == user.external_id

    async def test_get_by_external_id(self, db_session):
        await UserFactory.create(db_session, external_id="ext-001")

        repo = UserRepository()
        found = await repo.get_by_external_id(external_id="ext-001", db=db_session)

        assert found is not None
        assert found.external_id == "ext-001"

    async def test_get_by_external_id_returns_none_when_missing(self, db_session):
        repo = UserRepository()
        result = await repo.get_by_external_id(external_id="ghost", db=db_session)
        assert result is None

    async def test_isolation_between_tests(self, db_session):
        # Verifies that clean_db ran: no user with "ext-001" should exist here
        repo = UserRepository()
        result = await repo.get_by_external_id(external_id="ext-001", db=db_session)
        assert result is None
