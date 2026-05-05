import pytest

BASE = "/api/v1/totems"

EXPECTED_TOTEM_COUNT = 60  # 9 criteria × 6 tiers + 6 global tiers (seeded by migration 0006)


@pytest.mark.integration
class TestGetAllTotems:

    async def test_returns_all_seeded_totems(self, client):
        response = await client.get(BASE + "/")

        assert response.status_code == 200
        assert len(response.json()) == EXPECTED_TOTEM_COUNT

    async def test_totem_has_expected_fields(self, client):
        response = await client.get(BASE + "/")
        totem = response.json()[0]

        assert "id" in totem
        assert "code" in totem
        assert "name" in totem

    async def test_global_totems_are_present(self, client):
        response = await client.get(BASE + "/")
        codes = {t["code"] for t in response.json()}

        assert "global_top_1_absolu" in codes
        assert "global_top_50_pct" in codes

    async def test_criterion_totems_are_present(self, client):
        response = await client.get(BASE + "/")
        codes = {t["code"] for t in response.json()}

        assert "clarte_des_idees_top_1_pct" in codes
        assert "respect_collaboration_top_50_pct" in codes
