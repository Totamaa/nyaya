from __future__ import annotations

from typing import Any, Iterable, Protocol, TypeVar, runtime_checkable


Message = dict[str, str]
SchemaT = TypeVar("SchemaT")


@runtime_checkable
class LLMClient(Protocol):
    def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        ...

    def stream_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[str]:
        ...

    def complete_structured(
        self,
        messages: list[Message],
        output_type: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> SchemaT:
        ...
