from __future__ import annotations

import json

from ..connectors.base import Message

from .constants import DEFAULT_SYSTEM_PROMPT, TEXT_CRITERIA
from .models import PreparedEvaluationInput


def _build_rubric_lines() -> list[str]:
    return [
        f"{index}. {criterion.name} ({criterion.weight_percent}%): {criterion.description}"
        for index, criterion in enumerate(TEXT_CRITERIA, start=1)
    ]


def build_evaluation_messages(
    prepared_input: PreparedEvaluationInput,
    *,
    system_prompt: str | None = None,
) -> list[Message]:
    schema = {
        criterion.name: {
            "score": "number between 1 and 5",
            "rationale": "short French rationale, max 2 short sentences",
        }
        for criterion in TEXT_CRITERIA
    }
    schema["analysis_summary"] = "short French summary, max 2 short sentences"
    schema["model_confidence"] = "float between 0 and 1"

    payload = {
        **prepared_input.prompt_payload(),
        "task": {
            "language": "fr",
            "scale": "Each criterion must be scored from 1 to 5.",
            "instructions": [
                "Évalue uniquement à partir du texte fourni et du contexte fourni.",
                "N'invente aucun contexte absent.",
                "N'évalue pas la vérité du monde réel.",
                "Pour `exactitude_verifiabilite`, juge seulement la qualité épistémique du message.",
                "Les rationales doivent être courtes.",
                "Réponds avec un JSON strict conforme au schéma.",
            ],
            "rubric": _build_rubric_lines(),
            "output_schema": schema,
        },
    }

    return [
        {"role": "system", "content": (system_prompt or DEFAULT_SYSTEM_PROMPT).strip()},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def build_single_criterion_messages(
    prepared_input: PreparedEvaluationInput,
    *,
    criterion_name: str,
    criterion_description: str,
    system_prompt: str | None = None,
) -> list[Message]:
    payload = {
        **prepared_input.prompt_payload(),
        "task": {
            "language": "fr",
            "criterion": criterion_name,
            "criterion_description": criterion_description,
            "scale": "Score only this criterion from 1 to 5.",
            "instructions": [
                "Évalue uniquement le critère demandé.",
                "N'invente aucun contexte absent.",
                "Réponds avec un JSON strict minimal.",
            ],
            "output_schema": {
                "score": "number between 1 and 5",
                "rationale": "short French rationale, max 2 short sentences",
            },
        },
    }
    return [
        {"role": "system", "content": (system_prompt or DEFAULT_SYSTEM_PROMPT).strip()},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]
