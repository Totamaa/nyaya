from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.model import UserModel
from app.modules.users.service import UserService


def _make_service(user_repo=None, message_repo=None) -> UserService:
    return UserService(
        logger=MagicMock(),
        session=AsyncMock(),
        request_id=str(uuid4()),
        user_repository=user_repo or AsyncMock(),
        message_repository=message_repo or AsyncMock(),
    )


@pytest.mark.unit
class TestUserServiceGetByExternalId:

    async def test_returns_response_when_user_exists(self):
        user = UserModel(external_id="ext-123")
        user.id = uuid4()

        repo = AsyncMock()
        repo.get_by_external_id.return_value = user

        service = _make_service(user_repo=repo)
        result = await service.get_by_external_id("ext-123")

        assert result.external_id == "ext-123"
        repo.get_by_external_id.assert_awaited_once()

    async def test_raises_when_user_not_found(self):
        repo = AsyncMock()
        repo.get_by_external_id.return_value = None

        service = _make_service(user_repo=repo)

        with pytest.raises(UserNotFoundException):
            await service.get_by_external_id("ghost")


@pytest.mark.unit
class TestUserServiceCreate:

    async def test_creates_and_returns_user(self):
        async def _assign_id(user, db):
            user.id = uuid4()

        repo = AsyncMock()
        repo.create.side_effect = _assign_id

        service = _make_service(user_repo=repo)
        result = await service.create("new-ext-id")

        assert result.external_id == "new-ext-id"
        repo.create.assert_awaited_once()
