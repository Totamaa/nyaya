import pytest

BASE = "/api/v1/messages"

VALID_PAYLOAD = {
    "content_id": "msg-ext-001",
    "content_type": "comment",
    "text": "This is a test message.",
    "created_at": "2024-06-15T10:00:00Z",
    "author_id": 42,
}


@pytest.mark.integration
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

    async def test_reuses_existing_user_if_already_present(self, client, db_session):
        from sqlalchemy import select
        from app.modules.users.model import UserModel

        second_payload = {**VALID_PAYLOAD, "content_id": "msg-ext-002"}

        await client.post(BASE + "/", json=VALID_PAYLOAD)
        await client.post(BASE + "/", json=second_payload)

        result = await db_session.execute(
            select(UserModel).where(UserModel.external_id == "42")
        )
        users = result.scalars().all()
        assert len(users) == 1

    async def test_creates_evaluation_alongside_message(self, client, db_session):
        from sqlalchemy import select
        from app.modules.evaluations.model import EvaluationModel
        from app.modules.messages.model import MessageModel

        await client.post(BASE + "/", json=VALID_PAYLOAD)

        result = await db_session.execute(
            select(MessageModel).where(MessageModel.external_id == VALID_PAYLOAD["content_id"])
        )
        message = result.scalars().one_or_none()
        assert message is not None

        eval_result = await db_session.execute(
            select(EvaluationModel).where(EvaluationModel.message_id == message.id)
        )
        evaluation = eval_result.scalars().one_or_none()
        assert evaluation is not None
        assert evaluation.score_total is not None
