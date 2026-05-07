from datetime import date

import pytest

from app.core.utils.date_lib import subtract_months
from tests.integration.helpers import insert_feedback, insert_user

USERS_BASE = "/api/v1/users"


@pytest.mark.integration
class TestUserFeedbacksHistory:

    async def test_returns_empty_list_for_new_user(self, client, db_session):
        user = await insert_user(db_session, "feedbacks-history-empty")
        response = await client.get(f"{USERS_BASE}/{user.external_id}/feedbacks")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_feedbacks_for_recent_months(self, client, db_session):
        user = await insert_user(db_session, "feedbacks-history-multi")

        today = date.today()
        await insert_feedback(db_session, user, subtract_months(today, 1), content="Feedback mois -1.")
        await insert_feedback(db_session, user, subtract_months(today, 2), content="Feedback mois -2.")

        response = await client.get(f"{USERS_BASE}/{user.external_id}/feedbacks")

        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_limit_restricts_results(self, client, db_session):
        user = await insert_user(db_session, "feedbacks-history-limit")

        today = date.today()
        await insert_feedback(db_session, user, subtract_months(today, 1))
        await insert_feedback(db_session, user, subtract_months(today, 2))

        # limit=1, offset=1 → month_range(1, 1) = (last_month, last_month) → 1 résultat
        response = await client.get(f"{USERS_BASE}/{user.external_id}/feedbacks?limit=1&offset=1")

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/feedbacks")
        assert response.status_code == 404
