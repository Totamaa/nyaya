from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CriterionDefinition:
    name: str
    weight_percent: int
    description: str


TEXT_CRITERIA: tuple[CriterionDefinition, ...] = (
    CriterionDefinition(
        "clarte_des_idees",
        10,
        "Idée principale explicite, phrases compréhensibles, termes précis, connecteurs clairs.",
    ),
    CriterionDefinition(
        "exactitude_verifiabilite",
        15,
        "Qualité épistémique de l'énoncé : distinction fait/opinion, prudence, formulations vérifiables, pas de certitude abusive.",
    ),
    CriterionDefinition(
        "pertinence",
        10,
        "Alignement avec le sujet, absence de digression, réponse adaptée au contexte du fil.",
    ),
    CriterionDefinition(
        "logique_coherence",
        15,
        "Structure argumentative, liens cause-effet compréhensibles, absence de contradiction interne.",
    ),
    CriterionDefinition(
        "absence_de_sophismes",
        15,
        "Absence de biais logique ou sophisme manifeste, dont ad hominem, faux dilemme et généralisation hâtive.",
    ),
    CriterionDefinition(
        "ouverture_d_esprit",
        10,
        "Nuance, reconnaissance de limites, acceptation possible de points valides, absence de certitude fermée.",
    ),
    CriterionDefinition(
        "volonte_de_comprendre",
        8,
        "Questions ouvertes, reformulations, recherche de clarification, effort explicite pour comprendre la position d'autrui.",
    ),
    CriterionDefinition(
        "contribution_utile",
        12,
        "Apporte une information, une solution, une piste ou une reformulation réellement utile à la discussion.",
    ),
    CriterionDefinition(
        "respect_collaboration",
        4,
        "Ton neutre ou constructif, absence d'attaque personnelle, recherche de solution commune.",
    ),
)

LIKES_CRITERION = CriterionDefinition(
    "likes",
    1,
    "Popularité relative du message, fournie déjà normalisée entre 0 et 1.",
)

ALL_CRITERIA: tuple[CriterionDefinition, ...] = TEXT_CRITERIA + (LIKES_CRITERION,)
TEXT_CRITERION_NAMES: tuple[str, ...] = tuple(item.name for item in TEXT_CRITERIA)
ALL_CRITERION_NAMES: tuple[str, ...] = tuple(item.name for item in ALL_CRITERIA)
CRITERION_WEIGHTS: dict[str, int] = {item.name: item.weight_percent for item in ALL_CRITERIA}

PROMPT_VERSION = "message_eval_prompt_v1"
EVALUATION_VERSION = "message_eval_v1"

DEFAULT_SYSTEM_PROMPT = (
    "Tu es un évaluateur de contributions textuelles sur un réseau social d'entreprise. "
    "Tu appliques strictement un rubric. "
    "Tu n'évalues jamais la vérité du monde réel ; tu évalues seulement la qualité du message fourni. "
    "Tu réponds uniquement avec un JSON strict, sans markdown, sans commentaire hors schéma."
)
