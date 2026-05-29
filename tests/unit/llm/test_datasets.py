from pathlib import Path

import pytest

from llm.evaluation.datasets import (
    EndToEndControlDataset,
    FallacyControlDataset,
    RangeControlDataset,
    RangeControlItem,
    equalize_range_datasets,
    load_dataset,
)
from llm.evaluation.models import MessageEvaluationInput


@pytest.mark.unit
def test_all_datasets_validate() -> None:
    dataset_dir = Path("tests/data/llm")
    dataset_paths = sorted(dataset_dir.glob("*.json"))
    assert dataset_paths

    loaded = [load_dataset(path) for path in dataset_paths]

    assert any(isinstance(item, FallacyControlDataset) for item in loaded)
    assert any(isinstance(item, EndToEndControlDataset) for item in loaded)
    assert sum(isinstance(item, RangeControlDataset) for item in loaded) >= 8


@pytest.mark.unit
def test_end_to_end_dataset_contains_low_and_full_context() -> None:
    dataset = load_dataset("tests/data/llm/message_eval_end_to_end.json")

    assert isinstance(dataset, EndToEndControlDataset)
    context_levels = {item.expected.context_completeness for item in dataset.items}
    assert "full" in context_levels
    assert "low" in context_levels


@pytest.mark.unit
def test_control_datasets_use_input_payload_shape() -> None:
    dataset_dir = Path("tests/data/llm")
    dataset_paths = sorted(dataset_dir.glob("*.json"))
    assert dataset_paths

    for path in dataset_paths:
        loaded = load_dataset(path)
        if isinstance(loaded, (EndToEndControlDataset, FallacyControlDataset, RangeControlDataset)):
            items = loaded.items

        for item in items:
            payload = item.input
            for key in ("content_id", "content_type", "text", "created_at", "author_id"):
                assert key in payload


@pytest.mark.unit
def test_range_item_supports_entree_message_input_payload() -> None:
    item = RangeControlItem.model_validate(
        {
            "id": "R-ENTREE-1",
            "input": {
                "content_id": "c_900",
                "content_type": "comment",
                "text": "Je ne suis pas d'accord avec cet argument.",
                "created_at": "2026-02-26T10:00:00Z",
                "author_id": 15,
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
                    "edito_id": 12,
                    "phase": "causes",
                    "topic_id": 3,
                    "tags": ["energie"],
                },
            },
            "expected_score_range": [4, 5],
        }
    )

    payload = item.to_message_input_payload(dataset_name="clarity_control")
    validated = MessageEvaluationInput.model_validate(payload)

    assert validated.content_id == "c_900"
    assert validated.parent is not None
    assert validated.parent.text == "Le nucléaire est dangereux car il produit des déchets."


@pytest.mark.unit
def test_equalize_range_datasets_downsamples_to_smallest_size() -> None:
    dataset_a = RangeControlDataset.model_validate(
        {
            "dataset_name": "dataset_a",
            "version": "v1",
            "language": "fr",
            "scale": {"min": 1, "max": 5},
            "criterion": "clarity",
            "items": [
                {
                    "id": "A1",
                    "input": {
                        "content_id": "a1",
                        "content_type": "comment",
                        "text": "msg 1",
                        "created_at": "2026-01-01T00:00:00Z",
                        "author_id": 1,
                    },
                    "expected_score_range": [4, 5],
                },
                {
                    "id": "A2",
                    "input": {
                        "content_id": "a2",
                        "content_type": "comment",
                        "text": "msg 2",
                        "created_at": "2026-01-01T00:00:00Z",
                        "author_id": 2,
                    },
                    "expected_score_range": [4, 5],
                },
                {
                    "id": "A3",
                    "input": {
                        "content_id": "a3",
                        "content_type": "comment",
                        "text": "msg 3",
                        "created_at": "2026-01-01T00:00:00Z",
                        "author_id": 3,
                    },
                    "expected_score_range": [4, 5],
                },
            ],
        }
    )
    dataset_b = RangeControlDataset.model_validate(
        {
            "dataset_name": "dataset_b",
            "version": "v1",
            "language": "fr",
            "scale": {"min": 1, "max": 5},
            "criterion": "clarity",
            "items": [
                {
                    "id": "B1",
                    "input": {
                        "content_id": "b1",
                        "content_type": "comment",
                        "text": "msg 1",
                        "created_at": "2026-01-01T00:00:00Z",
                        "author_id": 1,
                    },
                    "expected_score_range": [4, 5],
                },
                {
                    "id": "B2",
                    "input": {
                        "content_id": "b2",
                        "content_type": "comment",
                        "text": "msg 2",
                        "created_at": "2026-01-01T00:00:00Z",
                        "author_id": 2,
                    },
                    "expected_score_range": [4, 5],
                },
            ],
        }
    )

    equalized = equalize_range_datasets([dataset_a, dataset_b], seed=123)

    assert [len(dataset.items) for dataset in equalized] == [2, 2]
    assert {item.id for item in equalized[0].items}.issubset({"A1", "A2", "A3"})


@pytest.mark.unit
def test_equalize_range_datasets_rejects_too_large_target() -> None:
    dataset = RangeControlDataset.model_validate(
        {
            "dataset_name": "dataset_small",
            "version": "v1",
            "language": "fr",
            "scale": {"min": 1, "max": 5},
            "criterion": "clarity",
            "items": [
                {
                    "id": "S1",
                    "input": {
                        "content_id": "s1",
                        "content_type": "comment",
                        "text": "msg",
                        "created_at": "2026-01-01T00:00:00Z",
                        "author_id": 1,
                    },
                    "expected_score_range": [4, 5],
                }
            ],
        }
    )

    with pytest.raises(ValueError):
        equalize_range_datasets([dataset], target_size=2)
