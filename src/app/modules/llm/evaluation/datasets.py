from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class RangeControlItem(BaseModel):
    id: str
    previous_message: str
    message: str
    next_message: str
    expected_score_range: tuple[int, int]


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
    message: str
    context: str
    expected: FallacyExpectation


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


def load_dataset(path: str | Path) -> RangeControlDataset | FallacyControlDataset | EndToEndControlDataset:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "tested_fallacies" in data:
        return FallacyControlDataset.model_validate(data)
    if data.get("dataset_name") == "message_eval_end_to_end":
        return EndToEndControlDataset.model_validate(data)
    return RangeControlDataset.model_validate(data)
