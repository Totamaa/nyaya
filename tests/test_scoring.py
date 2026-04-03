from llm.evaluation.constants import ALL_CRITERION_NAMES
from llm.evaluation.models import CriterionAssessment, LLMMessageEvaluationOutput
from llm.evaluation.scoring import build_scores, compute_likes_score, compute_weighted_score


def build_llm_output(score: float = 5.0) -> LLMMessageEvaluationOutput:
    payload = {
        name: {"score": score, "rationale": f"{name} ok"}
        for name in ALL_CRITERION_NAMES
        if name != "likes"
    }
    payload["analysis_summary"] = "Résumé."
    payload["context_completeness"] = "full"
    payload["model_confidence"] = 0.9
    return LLMMessageEvaluationOutput.model_validate(payload)


def test_compute_likes_score() -> None:
    assert compute_likes_score(0.0) == 1.0
    assert compute_likes_score(0.5) == 3.0
    assert compute_likes_score(1.0) == 5.0


def test_weighted_score_with_all_criteria_maxed() -> None:
    output = build_llm_output()
    scores = build_scores(output, likes_normalized=1.0)

    assert set(scores) == set(ALL_CRITERION_NAMES)
    assert scores["likes"].score == 5.0

    weighted_score, score_100 = compute_weighted_score(scores)

    assert weighted_score == 1.0
    assert score_100 == 100.0


def test_weighted_score_uses_decimal_likes_score() -> None:
    output = build_llm_output(score=4.0)
    scores = build_scores(output, likes_normalized=0.5)
    weighted_score, score_100 = compute_weighted_score(scores)

    expected = round((0.99 * 0.8) + (0.01 * 0.6), 6)
    assert weighted_score == expected
    assert score_100 == round(expected * 100.0, 2)
