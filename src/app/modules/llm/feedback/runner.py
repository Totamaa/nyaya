from __future__ import annotations

from app.modules.llm.connectors.base import LLMClient
from app.modules.feedbacks.schemas import LLMFeedbackInput, LLMFeedbackResult


_SYSTEM_PROMPT = (
    "Tu es un coach de communication bienveillant et direct. "
    "Tu analyses les performances de communication d'un utilisateur sur un réseau social d'entreprise "
    "et tu lui fournis un feedback mensuel personnalisé, constructif et actionnable. "
    "Tu réponds uniquement en français."
)


def _build_messages(llm_input: LLMFeedbackInput) -> list[dict[str, str]]:
    lines = [
        f"Période : {llm_input.period}",
        "",
        "Voici les catégories où cet utilisateur a le plus de marge de progression, "
        "avec ses messages les moins bien notés :",
        "",
    ]
    for entry in llm_input.worst_categories:
        lines.append(f"### {entry.category} (moyenne : {entry.mean_score:.2f}/10)")
        for msg in entry.worst_messages:
            lines.append(f'- "{msg.text}" (score : {msg.score:.2f}/10)')
        lines.append("")

    lines += [
        "Rédige un feedback mensuel personnalisé de 3 à 5 paragraphes.",
        "Pour chaque catégorie, identifie le problème principal et propose une piste concrète d'amélioration.",
        "Adopte un ton bienveillant mais direct.",
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
    messages = _build_messages(llm_input)
    content = client.complete_text(messages, temperature=0.5)
    worst_cat_names = [entry.category for entry in llm_input.worst_categories]
    return LLMFeedbackResult(content=content, worst_categories=worst_cat_names)
