from pathlib import Path

from llm.evaluation.datasets import (
    EndToEndControlDataset,
    FallacyControlDataset,
    RangeControlDataset,
    load_dataset,
)


def test_all_datasets_validate() -> None:
    dataset_dir = Path("llm/test_dataset")
    dataset_paths = sorted(dataset_dir.glob("*.json"))
    assert dataset_paths

    loaded = [load_dataset(path) for path in dataset_paths]

    assert any(isinstance(item, FallacyControlDataset) for item in loaded)
    assert any(isinstance(item, EndToEndControlDataset) for item in loaded)
    assert sum(isinstance(item, RangeControlDataset) for item in loaded) >= 8


def test_end_to_end_dataset_contains_low_and_full_context() -> None:
    dataset = load_dataset("llm/test_dataset/message_eval_end_to_end.json")

    assert isinstance(dataset, EndToEndControlDataset)
    context_levels = {item.expected.context_completeness for item in dataset.items}
    assert "full" in context_levels
    assert "low" in context_levels
