import pytest


BASE = "/api/v1/messages"

VALID_PAYLOAD = {
    "content_id": "msg-ext-001",
    "content_type": "comment",
    "text": "This is a test message.",
    "created_at": "2024-06-15T10:00:00Z",
    "author_id": 42,
}


@pytest.mark.api
class TestCreateMessage:

    async def test_creates_message_and_returns_id(self, client):
        response = await client.post(BASE + "/", json=VALID_PAYLOAD)

        assert response.status_code == 201
        body = response.json()
        assert "id" in body

    async def test_creates_user_on_the_fly_if_missing(self, client, db_session):
        from sqlalchemy import select
        from app.modules.users.model import UserModel

        await client.post(BASE + "/", json=VALID_PAYLOAD)

        result = await db_session.execute(
            select(UserModel).where(UserModel.external_id == "42")
        )
        user = result.scalars().one_or_none()
        assert user is not None

    async def test_duplicate_content_id_returns_409(self, client):
        await client.post(BASE + "/", json=VALID_PAYLOAD)

        response = await client.post(BASE + "/", json=VALID_PAYLOAD)
        assert response.status_code == 409

    async def test_missing_required_field_returns_422(self, client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "text"}
        response = await client.post(BASE + "/", json=payload)
        assert response.status_code == 422

    async def test_auth_required_without_override(self, authed_client):
        response = await authed_client.post(BASE + "/", json=VALID_PAYLOAD)
        assert response.status_code == 201
