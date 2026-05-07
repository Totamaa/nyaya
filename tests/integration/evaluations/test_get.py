import pytest

from tests.integration.helpers import insert_evaluation, insert_message, insert_user

MESSAGES_BASE = "/api/v1/messages"
EVALUATIONS_BASE = "/api/v1/evaluations"

CRITERIA = [
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

CREATE_PAYLOAD = {
    "content_id": "msg-eval-smoke",
    "content_type": "comment",
    "text": "Un argument bien construit sur le sujet proposé.",
    "created_at": "2024-06-15T10:00:00Z",
    "author_id": 99,
}


@pytest.mark.integration
class TestGetEvaluation:

    async def test_returns_evaluation_with_all_criteria(self, client, db_session):
        """Direct DB insert — no LLM call needed to test the GET endpoint."""
        user = await insert_user(db_session, "eval-get-user")
        msg = await insert_message(db_session, user.id, external_id="eval-direct-001")
        await insert_evaluation(db_session, msg.id, score=7.5)

        response = await client.get(f"{EVALUATIONS_BASE}/eval-direct-001")

        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert "message_id" in body
        assert body["score_total"] == pytest.approx(7.5)
        for criterion in CRITERIA:
            assert criterion in body
            assert body[criterion] is not None

    async def test_post_message_creates_retrievable_evaluation(self, client):
        """Smoke test: full POST → GET flow triggers the evaluation pipeline once."""
        await client.post(MESSAGES_BASE + "/", json=CREATE_PAYLOAD)

        response = await client.get(f"{EVALUATIONS_BASE}/{CREATE_PAYLOAD['content_id']}")

        assert response.status_code == 200
        body = response.json()
        assert body["score_total"] is not None

    async def test_unknown_message_returns_404(self, client):
        response = await client.get(f"{EVALUATIONS_BASE}/does-not-exist")
        assert response.status_code == 404
