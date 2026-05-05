import pytest

BASE = "/api/v1/totems"


@pytest.mark.integration
class TestGetAllTotems:

    async def test_returns_empty_list_when_no_totems_seeded(self, client):
        response = await client.get(BASE + "/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_response_is_a_list(self, client):
        response = await client.get(BASE + "/")

        assert isinstance(response.json(), list)
