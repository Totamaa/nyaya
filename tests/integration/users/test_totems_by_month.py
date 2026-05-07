from datetime import date

import pytest

from tests.integration.helpers import insert_user, insert_user_totem

USERS_BASE = "/api/v1/users"


@pytest.mark.integration
class TestUserTotemsByMonth:

    async def test_returns_empty_list_for_user_with_no_totems(self, client, db_session):
        user = await insert_user(db_session, "totems-month-empty")
        response = await client.get(f"{USERS_BASE}/{user.external_id}/2024-06/totems")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_assigned_totems_for_requested_month(self, client, db_session):
        user = await insert_user(db_session, "totems-month-has-data")
        month = date(2024, 6, 1)
        await insert_user_totem(db_session, user.id, month, totem_code="global_top_50_pct", score_snapshot=6.5)

        response = await client.get(f"{USERS_BASE}/{user.external_id}/2024-06/totems")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["totem"]["code"] == "global_top_50_pct"
        assert body[0]["score_snapshot"] == pytest.approx(6.5)

    async def test_filters_to_requested_month_only(self, client, db_session):
        user = await insert_user(db_session, "totems-month-filter")
        await insert_user_totem(db_session, user.id, date(2024, 6, 1), totem_code="global_top_50_pct")
        await insert_user_totem(db_session, user.id, date(2024, 5, 1), totem_code="global_top_25_pct")

        response = await client.get(f"{USERS_BASE}/{user.external_id}/2024-06/totems")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["totem"]["code"] == "global_top_50_pct"

    async def test_unknown_user_returns_404(self, client):
        response = await client.get(f"{USERS_BASE}/ghost-user/2024-06/totems")
        assert response.status_code == 404

    async def test_invalid_date_format_returns_400(self, client, db_session):
        user = await insert_user(db_session, "totems-month-badformat")
        response = await client.get(f"{USERS_BASE}/{user.external_id}/not-a-date/totems")
        assert response.status_code == 400
