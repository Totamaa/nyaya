"""0006_seed_totem

Revision ID: 63efc23175fc
Revises: abd3a7dad994
Create Date: 2026-04-22 18:58:28.448220

"""
from itertools import product
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '63efc23175fc'
down_revision: Union[str, Sequence[str], None] = 'abd3a7dad994'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (code_key, display_name)
CRITERIA = [
    ("clarte_des_idees",       "Clarté"),
    ("exactitude_verifiabilite", "Exactitude"),
    ("pertinence",             "Pertinence"),
    ("logique_coherence",      "Logique"),
    ("absence_de_sophismes",   "Raisonnement"),
    ("ouverture_d_esprit",     "Ouverture"),
    ("volonte_de_comprendre",  "Compréhension"),
    ("contribution_utile",     "Contribution"),
    ("respect_collaboration",  "Respect"),
]

# (suffix, label, description, threshold_or_None)
TIERS = [
    ("top_1_absolu", "Leader", "Premier de sa catégorie sur l'ensemble des utilisateurs.", None),
    ("top_1_pct",    "Élite",          "Dans le top 1 % des utilisateurs.",                        1.0),
    ("top_5_pct",    "Expert",         "Dans le top 5 % des utilisateurs.",                        5.0),
    ("top_10_pct",   "Avancé",         "Dans le top 10 % des utilisateurs.",                       10.0),
    ("top_25_pct",   "Confirmé",       "Dans le top 25 % des utilisateurs.",                       25.0),
    ("top_50_pct",   "Actif",          "Dans le top 50 % des utilisateurs.",                       50.0),
]


def _rows() -> list[str]:
    rows = []

    for (crit_key, crit_name), (tier_suffix, tier_label, tier_desc, threshold) in product(CRITERIA, TIERS):
        code  = f"{crit_key}_{tier_suffix}"
        name  = f"{crit_name} - {tier_label}".replace("'", "''")
        desc  = f"{tier_desc} Critère évalué : {crit_name}.".replace("'", "''")
        thresh = str(threshold) if threshold is not None else "NULL"
        rows.append(
            f"(gen_random_uuid(), NOW(), NOW(), '{code}', '{name}', '{desc}', '{crit_key}', {thresh})"
        )

    for tier_suffix, tier_label, tier_desc, threshold in TIERS:
        code  = f"global_{tier_suffix}"
        name  = f"Global — {tier_label}".replace("'", "''")
        desc  = f"{tier_desc} Score global toutes catégories.".replace("'", "''")
        thresh = str(threshold) if threshold is not None else "NULL"
        rows.append(
            f"(gen_random_uuid(), NOW(), NOW(), '{code}', '{name}', '{desc}', 'global', {thresh})"
        )

    return rows


def upgrade() -> None:
    rows = _rows()
    op.execute(
        f"""
        INSERT INTO totems (id, created_at, updated_at, code, name, description, category, threshold)
        VALUES {", ".join(rows)}
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    codes = ", ".join(
        f"'{crit_key}_{tier_suffix}'"
        for crit_key, _ in CRITERIA
        for tier_suffix, *_ in TIERS
    )
    global_codes = ", ".join(f"'global_{tier_suffix}'" for tier_suffix, *_ in TIERS)
    op.execute(f"DELETE FROM totems WHERE code IN ({codes}, {global_codes})")
