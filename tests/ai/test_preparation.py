from llm.evaluation.models import MessageEvaluationInput
from llm.evaluation.preparation import prepare_message_for_evaluation


def test_prepare_comment_builds_textual_context_and_full_completeness() -> None:
    raw = MessageEvaluationInput.model_validate(
        {
            "content_id": "c_900",
            "content_type": "comment",
            "text": "Je ne suis pas d'accord avec cet argument.",
            "created_at": "2026-02-26T10:00:00Z",
            "author_id": 15,
            "tenant_id": "nyaya-demo",
            "parent": {
                "content_id": "c_842",
                "text": "Le nucléaire est dangereux car il produit des déchets.",
                "author_id": 9,
                "created_at": "2026-02-26T09:30:00Z",
            },
            "thread_root": {
                "content_id": "c_842",
                "text": "Le nucléaire est dangereux car il produit des déchets.",
            },
            "context": {
                "phase": "causes",
                "topic_label": "énergie nucléaire",
                "tags": ["energie"],
            },
        }
    )

    prepared = prepare_message_for_evaluation(raw)

    assert prepared.parent_text == "Le nucléaire est dangereux car il produit des déchets."
    assert prepared.thread_root_text == "Le nucléaire est dangereux car il produit des déchets."
    assert prepared.context_completeness == "full"
    assert prepared.context_text == "Phase: causes. Sujet: énergie nucléaire. Tags: energie."


def test_prepare_legacy_flat_payload_remains_supported() -> None:
    raw = MessageEvaluationInput.model_validate(
        {
            "content_id": "legacy-1",
            "content_type": "comment",
            "text": "Je ne suis pas convaincu.",
            "created_at": "2026-02-26T10:00:00Z",
            "author_id": 15,
            "parent_text": "Il faut supprimer cette étape.",
            "tenant_id": "nyaya-demo",
        }
    )

    prepared = prepare_message_for_evaluation(raw)

    assert raw.parent is not None
    assert raw.parent.text == "Il faut supprimer cette étape."
    assert prepared.context_completeness == "full"
