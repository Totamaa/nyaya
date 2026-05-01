from uuid import UUID

from app.modules.totems.schemas import TotemAssignment

CRITERIA = [
    "clarte_des_idees",
    "exactitude_verifiabilite",
    "pertinence",
    "logique_coherence",
    "absence_de_sophismes",
    "ouverture_d_esprit",
    "volonte_de_comprendre",
    "contribution_utile",
    "respect_collaboration",
]

# Paliers ordonnés du plus exclusif au plus large
# (seuil percentile ou None pour le #1 absolu, code_suffix)
TIERS: list[tuple[float | None, str]] = [
    (None, "top_1_absolu"),
    (1.0,  "top_1_pct"),
    (5.0,  "top_5_pct"),
    (10.0, "top_10_pct"),
    (25.0, "top_25_pct"),
    (50.0, "top_50_pct"),
]


def _best_tier_suffix(
    user_id: UUID,
    ranking: list[tuple[UUID, float]],
) -> tuple[str, float] | None:
    """
    Retourne (tier_suffix, score) du meilleur palier atteint, ou None si hors top 50%.
    Rang 1 absolu → top_1_absolu. Sinon percentile exact.
    """
    user_ids = [uid for uid, _ in ranking]
    if user_id not in user_ids:
        return None

    idx = user_ids.index(user_id)
    rank = idx + 1
    score = ranking[idx][1]
    n = len(ranking)

    if rank == 1:
        return ("top_1_absolu", score)

    pct = rank / n * 100
    if pct <= 1.0:
        return ("top_1_pct", score)
    if pct <= 5.0:
        return ("top_5_pct", score)
    if pct <= 10.0:
        return ("top_10_pct", score)
    if pct <= 25.0:
        return ("top_25_pct", score)
    if pct <= 50.0:
        return ("top_50_pct", score)
    return None


def compute_totem_assignments(
    user_id: UUID,
    criteria_rankings: list[tuple[str, list[tuple[UUID, float]]]],
    global_ranking: list[tuple[UUID, float]],
) -> list[TotemAssignment]:
    """
    Détermine le meilleur totem par catégorie (critères + global) pour un user.
    Entrées : rankings pré-calculés. Aucun appel DB.
    """
    assignments: list[TotemAssignment] = []

    for crit_key, ranking in criteria_rankings:
        result = _best_tier_suffix(user_id, ranking)
        if result is None:
            continue
        tier_suffix, score = result
        assignments.append(TotemAssignment(
            totem_code=f"{crit_key}_{tier_suffix}",
            score_snapshot=round(score, 2),
        ))

    result = _best_tier_suffix(user_id, global_ranking)
    if result is not None:
        tier_suffix, score = result
        assignments.append(TotemAssignment(
            totem_code=f"global_{tier_suffix}",
            score_snapshot=round(score, 2),
        ))

    return assignments
