from __future__ import annotations

import json

from llm.connectors.base import Message

from .constants import DEFAULT_SYSTEM_PROMPT, TEXT_CRITERIA
from .models import MessageEvaluationInput


def _build_rubric_lines() -> list[str]:
    lines: list[str] = []
    for index, criterion in enumerate(TEXT_CRITERIA, start=1):
        lines.append(
            f"{index}. {criterion.name} ({criterion.weight_percent}%): {criterion.description}"
        )
    return lines


def build_evaluation_messages(
    message_input: MessageEvaluationInput,
    *,
    system_prompt: str | None = None,
) -> list[Message]:
    schema = {
        criterion.name: {
            "score": "integer between 1 and 5",
            "rationale": "short French rationale, 1 to 3 sentences",
        }
        for criterion in TEXT_CRITERIA
    }
    schema["analysis_summary"] = "short French summary"
    schema["context_completeness"] = "one of: full, partial, low"
    schema["model_confidence"] = "float between 0 and 1"

    payload = {
        "message": {
            "content_id": message_input.content_id,
            "content_type": message_input.content_type,
            "text": message_input.text,
            "created_at": message_input.created_at.isoformat(),
            "author_id": message_input.author_id,
        },
        "context": message_input.context_snapshot(),
        "task": {
            "language": "fr",
            "scale": "Each criterion must be scored from 1 to 5.",
            "instructions": [
                "Évalue uniquement à partir du texte fourni et du contexte fourni.",
                "N'invente aucun contexte absent.",
                "N'évalue pas la vérité du monde réel.",
                "Pour `exactitude_verifiabilite`, juge seulement la qualité épistémique du message.",
                "Réponds avec un JSON strict conforme au schéma.",
            ],
            "rubric": _build_rubric_lines(),
            "output_schema": schema,
        },
    }

    return [
        {"role": "system", "content": (system_prompt or DEFAULT_SYSTEM_PROMPT).strip()},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, indent=2),
        },
    ]
