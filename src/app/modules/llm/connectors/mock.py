from __future__ import annotations

import random
from typing import Any, Iterable

from .base import Message


class MockLLMClient:
    def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        return "Mock LLM response."

    def stream_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[str]:
        yield "Mock LLM response."

    def complete_structured(
        self,
        messages: list[Message],
        output_type: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        from app.modules.llm.evaluation.constants import TEXT_CRITERION_NAMES

        fields = {
            name: {"score": round(random.uniform(1.0, 5.0), 2), "rationale": "Mock rationale."}
            for name in TEXT_CRITERION_NAMES
        }
        return output_type(
            **fields,
            analysis_summary="Mock analysis summary.",
            model_confidence=round(random.uniform(0.5, 1.0), 2),
        )
