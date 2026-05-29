from __future__ import annotations

from app.modules.llm.connectors.base import LLMClient

from .constants import DEFAULT_SYSTEM_PROMPT
from .models import LLMMessageEvaluationOutput, MessageEvaluationInput
from .preparation import prepare_message_for_evaluation
from .prompt import build_evaluation_messages


_WEIGHTS: dict[str, float] = {
    "clarte_des_idees": 0.10,
    "exactitude_verifiabilite": 0.15,
    "pertinence": 0.10,
    "logique_coherence": 0.15,
    "absence_de_sophismes": 0.15,
    "ouverture_d_esprit": 0.10,
    "volonte_de_comprendre": 0.08,
    "contribution_utile": 0.12,
    "respect_collaboration": 0.04,
}


def evaluate_message(client: LLMClient, eval_input: MessageEvaluationInput) -> dict[str, float]:
    """Évalue un message via le LLM. Retourne les scores par critère (0-10) + score_total (0-10)."""
    prepared = prepare_message_for_evaluation(eval_input)
    messages = build_evaluation_messages(prepared, system_prompt=DEFAULT_SYSTEM_PROMPT)

    llm_output: LLMMessageEvaluationOutput = client.complete_structured(
        messages,
        LLMMessageEvaluationOutput,
        temperature=0.0,
        max_tokens=1600,
    )

    def _to_ten(score_1_5: float) -> float:
        return round((score_1_5 - 1.0) / 4.0 * 10.0, 2)

    scores = {k: _to_ten(getattr(llm_output, k).score) for k in _WEIGHTS}
    scores["score_total"] = round(sum(scores[k] * w for k, w in _WEIGHTS.items()), 2)
    return scores
