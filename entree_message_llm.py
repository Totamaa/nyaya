from cloudinit.user_data import CONTENT_TYPE
ENTREE_MESSAGE = {
    "content_id": "c_900",
    "content_type": "comment",
    "text": "Je ne suis pas d'accord avec cet argument.",
    "created_at": "2026-02-26T10:00:00Z",
    "author_id": 15,
    "parent": {
        "content_id": "c_842",
        "text": "Le nucléaire est dangereux car il produit des déchets.",
        "author_id": 9,
        "created_at": "2026-02-26T09:30:00Z",
    },
    "thread_root": {
        "content_id": "c_842",
        "text": "Le nucléaire est dangereux car il produit des déchets.",
    },
    "context": {
        "edito_id": 12,
        "phase": "causes",
        "topic_id": 3,
        "tags": ["energie"],
    },
}

content_type
text 
parent.text
thread_root.text 
context 


# Adrien renvoie 

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class MessageEvaluation(BaseModel):
    """
    Évaluation d'un message selon 10 critères (total: 100%).
    Domaines: Critique (65%), Constructif (34%), Métadonnée (1%).
    """

    # === Critères Critiques (65%) ===
    clarte_des_idees: float = Field(
        default=0.0,
        description="Clarté des idées (10%) - Idée principale explicite, phrases compréhensibles, termes précis, connecteurs clairs"
    )
    exactitude_verifiabilite: float = Field(
        default=0.0,
        description="Exactitude / Vérifiabilité (15%) - Faits vérifiables, sources fiables, distinction fait/opinion"
    )
    pertinence: float = Field(
        default=0.0,
        description="Pertinence (10%) - Alignement avec le sujet, absence de digressions"
    )
    logique_coherence: float = Field(
        default=0.0,
        description="Logique & cohérence (15%) - Structure argumentative, liens cause→effet, absence de contradictions"
    )
    absence_de_sophismes: float = Field(
        default=0.0,
        description="Absence de sophismes (15%) - Aucun biais logique, pas d'ad hominem, pas de causalité fausse"
    )

    # === Critères Constructifs (34%) ===
    ouverture_d_esprit: float = Field(
        default=0.0,
        description="Ouverture d'esprit (10%) - Reconnaissance de limites, acceptation de points valides, nuance"
    )
    volonte_de_comprendre: float = Field(
        default=0.0,
        description="Volonté de comprendre (8%) - Questions ouvertes, reformulations, clarifications"
    )
    contribution_utile: float = Field(
        default=0.0,
        description="Contribution utile (12%) - Informations nouvelles, solutions, perspectives, valeur ajoutée"
    )
    respect_collaboration: float = Field(
        default=0.0,
        description="Respect & collaboration (4%) - Ton neutre ou bienveillant, recherche de solution commune"
    )

    # === Métadonnée (1%) ===
    likes: float = Field(
        default=0.0,
        description="Likes (1%) - Popularité relative du message (normalisée 0-1)"
    )

    # === Métadonnées temporelles ===
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def score_total(self) -> float:
        """Calcule le score total pondéré (sur 100)."""
        return (
            self.clarte_des_idees * 0.10 +
            self.exactitude_verifiabilite * 0.15 +
            self.pertinence * 0.10 +
            self.logique_coherence * 0.15 +
            self.absence_de_sophismes * 0.15 +
            self.ouverture_d_esprit * 0.10 +
            self.volonte_de_comprendre * 0.08 +
            self.contribution_utile * 0.12 +
            self.respect_collaboration * 0.04 +
            self.likes * 0.01
        )



## Badges