from datetime import date

import pytest

from tests.integration.helpers import insert_feedback, insert_user

USERS_BASE = "/api/v1/users"


@pytest.mark.integration
class TestUserFeedbackByMonth:

    async def test_returns_404_when_no_feedback_generated(self, client, db_session):
        user = await insert_user(db_session, "feedback-month-none")
        response = await client.get(f"{USERS_BASE}/{user.external_id}/2024-06/feedback")

        assert response.status_code == 404

    async def test_returns_feedback_when_exists(self, client, db_session):
        user = await insert_user(db_session, "feedback-month-exists")
        await insert_feedback(db_session, user, date(2024, 6, 1), content="Super feedback de juin.")

        response = await client.get(f"{USERS_BASE}/{user.external_id}/2024-06/feedback")

        assert response.status_code == 200
        body = response.json()
        assert body["content"] == "Super feedback de juin."
        assert body["user_external_id"] == user.external_id

    async def test_feedback_has_expected_fields(self, client, db_session):
        user = await insert_user(db_session, "feedback-month-fields")
        await insert_feedback(db_session, user, date(2024, 6, 1))

        response = await client.get(f"{USERS_BASE}/{user.external_id}/2024-06/feedback")

        body = response.json()
        assert "id" in body
        assert "user_id" in body
        assert "user_external_id" in body
        assert "month" in body
        assert "content" in body
        assert "worst_categories" in body
        assert "generated_at" in body

    async def test_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/2024-06/feedback")
        assert response.status_code == 404

    async def test_invalid_date_format_returns_400(self, client, db_session):
        user = await insert_user(db_session, "feedback-month-badformat")
        response = await client.get(f"{USERS_BASE}/{user.external_id}/not-a-date/feedback")
        assert response.status_code == 400
