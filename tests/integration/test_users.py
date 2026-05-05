import pytest

MESSAGES_BASE = "/api/v1/messages"
USERS_BASE = "/api/v1/users"

CREATE_PAYLOAD = {
    "content_id": "msg-user-001",
    "content_type": "comment",
    "text": "Message pour créer un utilisateur.",
    "created_at": "2024-06-15T10:00:00Z",
    "author_id": 77,
}
USER_EXTERNAL_ID = "77"


async def _create_user(client) -> None:
    await client.post(MESSAGES_BASE + "/", json=CREATE_PAYLOAD)


@pytest.mark.integration
class TestUserTotems:

    async def test_get_totems_by_month_returns_empty_list(self, client):
        await _create_user(client)
        response = await client.get(f"{USERS_BASE}/{USER_EXTERNAL_ID}/2024-06/totems")

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_totems_history_returns_empty_list(self, client):
        await _create_user(client)
        response = await client.get(f"{USERS_BASE}/{USER_EXTERNAL_ID}/totems")

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_totems_by_month_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/2024-06/totems")
        assert response.status_code == 404

    async def test_get_totems_history_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/totems")
        assert response.status_code == 404

    async def test_get_totems_by_month_invalid_format_returns_400(self, client):
        await _create_user(client)
        response = await client.get(f"{USERS_BASE}/{USER_EXTERNAL_ID}/not-a-date/totems")
        assert response.status_code == 400


@pytest.mark.integration
class TestUserFeedbacks:

    async def test_get_feedbacks_history_returns_empty_list(self, client):
        await _create_user(client)
        response = await client.get(f"{USERS_BASE}/{USER_EXTERNAL_ID}/feedbacks")

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_feedback_by_month_returns_404_when_not_generated(self, client):
        await _create_user(client)
        response = await client.get(f"{USERS_BASE}/{USER_EXTERNAL_ID}/2024-06/feedback")

        assert response.status_code == 404

    async def test_get_feedbacks_history_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/feedbacks")
        assert response.status_code == 404

    async def test_get_feedback_by_month_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/2024-06/feedback")
        assert response.status_code == 404

    async def test_get_feedback_by_month_invalid_format_returns_400(self, client):
        await _create_user(client)
        response = await client.get(f"{USERS_BASE}/{USER_EXTERNAL_ID}/not-a-date/feedback")
        assert response.status_code == 400
