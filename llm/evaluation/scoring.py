from __future__ import annotations

from collections import OrderedDict

from .constants import ALL_CRITERIA, TEXT_CRITERION_NAMES
from .models import CriterionAssessment, LLMMessageEvaluationOutput


def compute_likes_score(likes_normalized: float) -> float:
    return round(1.0 + (4.0 * float(likes_normalized)), 4)


def build_scores(
    llm_output: LLMMessageEvaluationOutput,
    *,
    likes_normalized: float,
) -> OrderedDict[str, CriterionAssessment]:
    scores: OrderedDict[str, CriterionAssessment] = OrderedDict()
    text_scores = llm_output.text_scores()
    for name in TEXT_CRITERION_NAMES:
        scores[name] = text_scores[name]

    scores["likes"] = CriterionAssessment(
        score=compute_likes_score(likes_normalized),
        rationale=(
            "Calcul déterministe hors LLM à partir de "
            f"`likes_normalized={likes_normalized:.4f}`."
        ),
    )
    return scores


def compute_weighted_score(scores: dict[str, CriterionAssessment]) -> tuple[float, float]:
    score_norm = 0.0
    for criterion in ALL_CRITERIA:
        criterion_score = scores[criterion.name].score
        score_norm += (criterion_score / 5.0) * (criterion.weight_percent / 100.0)
    score_norm = round(score_norm, 6)
    score_100 = round(score_norm * 100.0, 2)
    return score_norm, score_100
