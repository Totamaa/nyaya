from __future__ import annotations

from typing import Any

from .models import MessageContext, MessageEvaluationInput, PreparedEvaluationInput


def _context_to_text(context: MessageContext | None) -> str | None:
    if context is None:
        return None

    parts: list[str] = []
    if context.phase:
        parts.append(f"Phase: {context.phase}")
    if context.topic_label:
        parts.append(f"Sujet: {context.topic_label}")
    if context.edito_title:
        parts.append(f"Cadre éditorial: {context.edito_title}")
    if context.tags:
        parts.append("Tags: " + ", ".join(context.tags))

    extras = context.model_extra or {}
    for key, value in extras.items():
        if value in (None, "", [], {}):
            continue
        if key in {"edito_id", "topic_id"}:
            continue
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value if str(item).strip())
            if rendered:
                parts.append(f"{key}: {rendered}")
            continue
        if isinstance(value, (str, int, float, bool)):
            parts.append(f"{key}: {value}")

    if not parts:
        return None
    return ". ".join(parts) + "."


def infer_context_completeness(message_input: MessageEvaluationInput, context_text: str | None) -> str:
    if message_input.content_type == "post":
        return "full"
    if message_input.parent and message_input.parent.text:
        return "full"
    if message_input.thread_root and message_input.thread_root.text:
        return "partial"
    if context_text:
        return "partial"
    return "low"


def prepare_message_for_evaluation(message_input: MessageEvaluationInput) -> PreparedEvaluationInput:
    context_text = _context_to_text(message_input.context)
    return PreparedEvaluationInput(
        content_id=message_input.content_id,
        content_type=message_input.content_type,
        text=message_input.text,
        created_at=message_input.created_at,
        author_id=message_input.author_id,
        tenant_id=message_input.tenant_id,
        likes_normalized=message_input.likes_normalized,
        parent_text=(message_input.parent.text if message_input.parent else None),
        thread_root_text=(message_input.thread_root.text if message_input.thread_root else None),
        context_text=context_text,
        context_completeness=infer_context_completeness(message_input, context_text),
    )
