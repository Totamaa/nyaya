import pytest

MESSAGES_BASE = "/api/v1/messages"
EVALUATIONS_BASE = "/api/v1/evaluations"

CREATE_PAYLOAD = {
    "content_id": "msg-eval-001",
    "content_type": "comment",
    "text": "Un argument bien construit sur le sujet proposé.",
    "created_at": "2024-06-15T10:00:00Z",
    "author_id": 99,
}


@pytest.mark.integration
class TestGetEvaluation:

    async def test_returns_evaluation_after_message_creation(self, client):
        await client.post(MESSAGES_BASE + "/", json=CREATE_PAYLOAD)

        response = await client.get(f"{EVALUATIONS_BASE}/{CREATE_PAYLOAD['content_id']}")

        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert "message_id" in body
        assert "score_total" in body
        assert body["score_total"] is not None

    async def test_evaluation_contains_all_criteria(self, client):
        await client.post(MESSAGES_BASE + "/", json=CREATE_PAYLOAD)

        response = await client.get(f"{EVALUATIONS_BASE}/{CREATE_PAYLOAD['content_id']}")

        body = response.json()
        expected_criteria = [
            "clarte_des_idees",
            "exactitude_verifiabilite",
            "pertinence",
            "logique_coherence",
            "absence_de_sophismes",
            "ouverture_d_esprit",
            "volonte_de_comprendre",
            "contribution_utile",
            "respect_collaboration",
        ]
        for criterion in expected_criteria:
            assert criterion in body
            assert body[criterion] is not None

    async def test_unknown_message_returns_404(self, client):
        response = await client.get(f"{EVALUATIONS_BASE}/does-not-exist")
        assert response.status_code == 404
