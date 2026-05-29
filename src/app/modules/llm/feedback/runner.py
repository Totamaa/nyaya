from __future__ import annotations

from app.core.config.logs import get_logger
from app.modules.llm.connectors.base import LLMClient
from app.modules.feedbacks.schemas import LLMFeedbackInput, LLMFeedbackResult

logger = get_logger()
_TAG = "LLM:FeedbackRunner"


_SYSTEM_PROMPT = (
    "Coach de communication bienveillant. "
    "Feedback direct et actionnable, dans la langue des messages fournis, sans introduction ni conclusion générique."
)


def _build_messages(llm_input: LLMFeedbackInput) -> list[dict[str, str]]:
    lines = [f"Période : {llm_input.period}", ""]
    for entry in llm_input.worst_categories:
        examples = " / ".join(f'"{m.text[:100]}"' for m in entry.worst_messages[:2])
        lines.append(f"• {entry.category} ({entry.mean_score:.1f}/10) — {examples}")

    lines += [
        "",
        "Pour chaque catégorie : 1 phrase sur le problème, 1 conseil concret.",
        "Format strict : « • Catégorie : [problème]. [conseil]. »",
    ]

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


def generate_feedback(
    client: LLMClient,
    llm_input: LLMFeedbackInput,
) -> LLMFeedbackResult:
    """Génère le feedback mensuel via le LLM.

    Conçu pour être appelé via asyncio.to_thread depuis un service async.
    """
    logger.info(_TAG, "Generating feedback", extra=f"user_id={llm_input.user_id} period={llm_input.period}")
    messages = _build_messages(llm_input)
    content = client.complete_text(messages, temperature=0.5)
    worst_cat_names = [entry.category for entry in llm_input.worst_categories]
    logger.info(_TAG, "Feedback generated", extra=f"user_id={llm_input.user_id} len={len(content)}")
    return LLMFeedbackResult(content=content, worst_categories=worst_cat_names)
