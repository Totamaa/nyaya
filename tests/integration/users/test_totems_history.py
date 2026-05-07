from datetime import date

import pytest

from app.core.utils.date_lib import subtract_months
from tests.integration.helpers import insert_user, insert_user_totem

USERS_BASE = "/api/v1/users"


@pytest.mark.integration
class TestUserTotemsHistory:

    async def test_returns_empty_list_for_new_user(self, client, db_session):
        user = await insert_user(db_session, "totems-history-empty")
        response = await client.get(f"{USERS_BASE}/{user.external_id}/totems")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_totems_across_months(self, client, db_session):
        user = await insert_user(db_session, "totems-history-multi")

        today = date.today()
        await insert_user_totem(db_session, user.id, subtract_months(today, 1), totem_code="global_top_50_pct")
        await insert_user_totem(db_session, user.id, subtract_months(today, 2), totem_code="global_top_25_pct")

        response = await client.get(f"{USERS_BASE}/{user.external_id}/totems")

        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_limit_restricts_results(self, client, db_session):
        user = await insert_user(db_session, "totems-history-limit")

        today = date.today()
        # limit=1 → month_range(1, 0) = (this_month, this_month) → seul ce mois apparaît
        await insert_user_totem(db_session, user.id, subtract_months(today, 0), totem_code="global_top_50_pct")
        await insert_user_totem(db_session, user.id, subtract_months(today, 1), totem_code="global_top_25_pct")

        response = await client.get(f"{USERS_BASE}/{user.external_id}/totems?limit=1")

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/totems")
        assert response.status_code == 404
