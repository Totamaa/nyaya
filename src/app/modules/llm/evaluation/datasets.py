from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RangeControlItem(BaseModel):
    id: str
    input: dict[str, object]
    expected_score_range: tuple[int, int]

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "RangeControlItem":
        text = self.input.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("`input.text` est requis quand `input` est fourni.")
        return self

    def to_message_input_payload(self, *, dataset_name: str) -> dict[str, object]:
        return dict(self.input)


class RangeControlDataset(BaseModel):
    dataset_name: str
    version: str
    language: str
    scale: dict[str, object]
    criterion: str | None = None
    items: list[RangeControlItem]


class FallacyExpectation(BaseModel):
    fallacy_present: Literal["yes", "no"]
    fallacy_type: str


class FallacyControlItem(BaseModel):
    id: str
    input: dict[str, object]
    expected: FallacyExpectation

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "FallacyControlItem":
        text = self.input.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("`input.text` est requis quand `input` est fourni.")
        return self

    def to_message_and_context(self) -> tuple[str, str]:
        message = str(self.input.get("text", "")).strip()
        context_text = _render_context_from_input(self.input)
        return message, (context_text or "Contexte non fourni.")

    def to_message_input_payload(self, *, dataset_name: str) -> dict[str, object]:
        return dict(self.input)


class FallacyControlDataset(BaseModel):
    dataset_name: str
    version: str
    language: str
    scale: dict[str, object]
    tested_fallacies: list[str]
    items: list[FallacyControlItem]


class EndToEndExpectation(BaseModel):
    context_completeness: Literal["full", "partial", "low"]
    expected_score_range: tuple[int, int]


class EndToEndControlItem(BaseModel):
    id: str
    input: dict[str, object]
    expected: EndToEndExpectation


class EndToEndControlDataset(BaseModel):
    dataset_name: str
    version: str
    language: str
    items: list[EndToEndControlItem]


def _render_context_from_input(payload: dict[str, object]) -> str:
    parts: list[str] = []
    parent = payload.get("parent")
    if isinstance(parent, dict):
        parent_text = parent.get("text")
        if isinstance(parent_text, str) and parent_text.strip():
            parts.append(f"Parent: {parent_text.strip()}")

    thread_root = payload.get("thread_root")
    if isinstance(thread_root, dict):
        root_text = thread_root.get("text")
        if isinstance(root_text, str) and root_text.strip():
            parts.append(f"Thread root: {root_text.strip()}")

    context = payload.get("context")
    if isinstance(context, dict):
        phase = context.get("phase")
        topic_label = context.get("topic_label")
        tags = context.get("tags")
        if isinstance(phase, str) and phase.strip():
            parts.append(f"Phase: {phase.strip()}")
        if isinstance(topic_label, str) and topic_label.strip():
            parts.append(f"Sujet: {topic_label.strip()}")
        if isinstance(tags, list):
            rendered_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
            if rendered_tags:
                parts.append("Tags: " + ", ".join(rendered_tags))

    return " | ".join(parts)


def equalize_range_datasets(
    datasets: list[RangeControlDataset],
    *,
    target_size: int | None = None,
    seed: int = 42,
) -> list[RangeControlDataset]:
    if not datasets:
        return []

    min_size = min(len(dataset.items) for dataset in datasets)
    effective_size = min_size if target_size is None else target_size
    if effective_size <= 0:
        raise ValueError("La taille cible doit être strictement positive.")

    too_small = [dataset.dataset_name for dataset in datasets if len(dataset.items) < effective_size]
    if too_small:
        raise ValueError(
            "Impossible d'égaliser: taille cible supérieure à certains datasets: "
            + ", ".join(too_small)
        )

    rng = random.Random(seed)
    equalized: list[RangeControlDataset] = []
    for dataset in datasets:
        if len(dataset.items) == effective_size:
            selected = list(dataset.items)
        else:
            indices = sorted(rng.sample(range(len(dataset.items)), effective_size))
            selected = [dataset.items[index] for index in indices]
        equalized.append(dataset.model_copy(update={"items": selected}))
    return equalized


def load_dataset(path: str | Path) -> RangeControlDataset | FallacyControlDataset | EndToEndControlDataset:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "tested_fallacies" in data:
        return FallacyControlDataset.model_validate(data)
    if data.get("dataset_name") == "message_eval_end_to_end":
        return EndToEndControlDataset.model_validate(data)
    return RangeControlDataset.model_validate(data)
