"""
Seed script — définitions de totems.

Crée dans la table `totems` :
  - 1 totem global × 2 paliers (top 1 %, top 5 %)
  - 9 catégories de critères × 2 paliers (top 1 %, top 5 %)
  → 20 totems au total, idempotent (on_conflict_do_nothing sur code).

Usage :
    python scripts/seed_totems.py
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config.database import AsyncSessionLocal, UnitOfWork
from app.modules.totems.model import TotemModel

# ---------------------------------------------------------------------------
# Définitions
# ---------------------------------------------------------------------------

CRITERIA: dict[str, str] = {
    "clarte_des_idees":         "Clarté des idées",
    "exactitude_verifiabilite": "Exactitude & vérifiabilité",
    "pertinence":               "Pertinence",
    "logique_coherence":        "Logique & cohérence",
    "absence_de_sophismes":     "Absence de sophismes",
    "ouverture_d_esprit":       "Ouverture d'esprit",
    "volonte_de_comprendre":    "Volonté de comprendre",
    "contribution_utile":       "Contribution utile",
    "respect_collaboration":    "Respect & collaboration",
}

# (threshold ou None pour absolu, code_suffix, label, description_prefix)
TIERS: list[tuple[float | None, str, str, str]] = [
    (None, "top_1_absolu", "Top 1",  "Le meilleur contributeur absolu"),
    (1.0,  "top_1_pct",   "Top 1%", "Dans le top 1%"),
    (5.0,  "top_5_pct",   "Top 5%", "Dans le top 5%"),
    (10.0, "top_10_pct",  "Top 10%","Dans le top 10%"),
    (25.0, "top_25_pct",  "Top 25%","Dans le top 25%"),
    (50.0, "top_50_pct",  "Top 50%","Dans le top 50%"),
]


def _build_definitions() -> list[dict]:
    now = datetime.now(timezone.utc)
    defs: list[dict] = []

    # Global
    for threshold, tier_suffix, tier_label, desc_prefix in TIERS:
        defs.append({
            "id": uuid.uuid4(),
            "created_at": now,
            "updated_at": now,
            "code": f"global_{tier_suffix}",
            "name": f"{tier_label} Global",
            "description": f"{desc_prefix} des contributeurs toutes catégories confondues.",
            "category": "global",
            "threshold": threshold,
        })

    # Par critère
    for crit_key, crit_label in CRITERIA.items():
        for threshold, tier_suffix, tier_label, desc_prefix in TIERS:
            defs.append({
                "id": uuid.uuid4(),
                "created_at": now,
                "updated_at": now,
                "code": f"{crit_key}_{tier_suffix}",
                "name": f"{tier_label} – {crit_label}",
                "description": f"{desc_prefix} des contributeurs sur le critère « {crit_label} ».",
                "category": crit_key,
                "threshold": threshold,
            })

    return defs


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

async def seed_totems() -> None:
    defs = _build_definitions()
    # 10 catégories (9 critères + global) × 6 paliers = 60
    print(f"Seeding {len(defs)} totems …")

    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session):
            stmt = pg_insert(TotemModel).values(defs).on_conflict_do_nothing(index_elements=["code"])
            await session.execute(stmt)

    print(f"  ✓ {len(defs)} totems insérés (existants ignorés)")
    print("Seed totems terminé.")


if __name__ == "__main__":
    asyncio.run(seed_totems())
