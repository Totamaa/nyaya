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
        "L'idée centrale est identifiable, phrases sans ambiguïté, termes adaptés. [1-2]=vague ou confus, [3]=compréhensible avec lacunes, [4-5]=clair et précis.",
    ),
    CriterionDefinition(
        "exactitude_verifiabilite",
        15,
        "Distinction fait/opinion marquée, affirmations nuancées ou sourcées. [1-2]=certitudes abusives ou invérifiables, [3]=mélange partiellement marqué, [4-5]=formulations prudentes et vérifiables.",
    ),
    CriterionDefinition(
        "pertinence",
        10,
        "Réponse directement ancrée dans le sujet ou la question précédente. [1-2]=hors sujet ou digression majeure, [3]=lien partiel avec le fil, [4-5]=réponse ciblée et sans digression.",
    ),
    CriterionDefinition(
        "logique_coherence",
        15,
        "Enchaînement logique des idées, absence de contradiction interne. [1-2]=incohérent ou contradictoire, [3]=logique suivable mais lacunaire, [4-5]=argumentation structurée sans contradiction.",
    ),
    CriterionDefinition(
        "absence_de_sophismes",
        15,
        "Pas d'ad hominem, faux dilemme, appel à l'autorité non justifié ou généralisation abusive. [1-2]=sophisme flagrant, [3]=raisonnement discutable mais pas manifeste, [4-5]=argumentation rigoureuse.",
    ),
    CriterionDefinition(
        "ouverture_d_esprit",
        10,
        "Nuance exprimée, limites de sa propre position reconnues, pas de rejet systématique. [1-2]=dogmatique ou fermé, [3]=quelques réserves exprimées, [4-5]=nuancé et ouvert aux points de vue contraires.",
    ),
    CriterionDefinition(
        "volonte_de_comprendre",
        8,
        "Effort visible pour saisir la position de l'autre : reformulation, question ouverte. [1-2]=ignore l'interlocuteur, [3]=réagit sans chercher à comprendre, [4-5]=reformule ou questionne activement.",
    ),
    CriterionDefinition(
        "contribution_utile",
        12,
        "Apport concret à la discussion : information nouvelle, solution, reformulation clarifiante. [1-2]=aucun apport identifiable, [3]=apport mineur ou redondant, [4-5]=contribution substantielle.",
    ),
    CriterionDefinition(
        "respect_collaboration",
        4,
        "Ton neutre ou constructif, absence d'attaque personnelle ou de mépris. [1-2]=agressif ou méprisant, [3]=neutre mais froid, [4-5]=ton positif et collaboratif.",
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
    "Tu es un évaluateur de messages sur un réseau social axé sur la discussion bienveillante et constructive. "
    "Tu appliques un rubric de qualité communicationnelle. "
    "Tu évalues uniquement la qualité formelle et argumentative du message, jamais la vérité des faits. "
    "Si le contexte est incomplet, évalue avec les informations disponibles et reflète l'incertitude dans model_confidence. "
    "Réponds uniquement avec un JSON strict, sans markdown ni texte hors schéma."
)
