"""
Seed script — remplit la BD avec des données réalistes via Faker.

Usage (depuis la racine du projet) :
    python scripts/seed.py
    python scripts/seed.py --users 20 --messages 30 --thread-ratio 0.3
"""
import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from faker import Faker

# Rendre le package `app` importable sans installation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import AsyncSessionLocal, UnitOfWork
from app.modules.evaluations.model import EvaluationModel
from app.modules.messages.model import MessageModel
from app.modules.users.model import UserModel

fake = Faker("fr_FR")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONTENT_TYPES = ["comment", "reply", "post"]
PHASES = ["deliberation", "consultation", "vote", None]
TAGS_POOL = [
    "economie", "sante", "education", "environnement", "justice",
    "logement", "transport", "culture", "numerique", "securite",
]

# Part des messages qui tombent dans la fenêtre du mois précédent
LAST_MONTH_RATIO = 0.80


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_score() -> float | None:
    if random.random() < 0.05:
        return None
    return round(random.uniform(0, 10), 2)


def _make_evaluation(message_id: uuid.UUID) -> EvaluationModel:
    scores = {
        "clarte_des_idees": _random_score(),
        "exactitude_verifiabilite": _random_score(),
        "pertinence": _random_score(),
        "logique_coherence": _random_score(),
        "absence_de_sophismes": _random_score(),
        "ouverture_d_esprit": _random_score(),
        "volonte_de_comprendre": _random_score(),
        "contribution_utile": _random_score(),
        "respect_collaboration": _random_score(),
    }
    values = [v for v in scores.values() if v is not None]
    score_total = round(sum(values) / len(values), 2) if values else None

    return EvaluationModel(
        message_id=message_id,
        likes=random.randint(0, 150),
        score_total=score_total,
        **scores,
    )


def _source_created_at(now: datetime) -> datetime:
    """80 % dans le mois précédent, 20 % dans le mois courant ou avant."""
    if random.random() < LAST_MONTH_RATIO:
        # quelque part dans le mois précédent
        first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 1:
            first_of_prev = first_of_current.replace(year=now.year - 1, month=12)
        else:
            first_of_prev = first_of_current.replace(month=now.month - 1)
        delta = (first_of_current - first_of_prev).total_seconds()
        return first_of_prev + timedelta(seconds=random.uniform(0, delta))
    else:
        # dans le mois courant ou les 3 mois précédents (hors fenêtre)
        offset_days = random.choice([
            random.randint(0, now.day - 1),          # mois courant
            random.randint(32, 120),                  # 1-4 mois en arrière
        ])
        return now - timedelta(days=offset_days, seconds=random.randint(0, 86400))


def _make_user() -> UserModel:
    return UserModel(external_id=str(uuid.uuid4()))


def _make_root_message(author_id: uuid.UUID, now: datetime) -> MessageModel:
    tags = random.sample(TAGS_POOL, k=random.randint(0, 3)) or None
    return MessageModel(
        external_id=str(uuid.uuid4()),
        content_type=random.choice(CONTENT_TYPES),
        text=fake.paragraph(nb_sentences=random.randint(2, 6)),
        source_created_at=_source_created_at(now),
        edito_id=random.randint(1, 50) if random.random() > 0.3 else None,
        topic_id=random.randint(1, 200) if random.random() > 0.2 else None,
        phase=random.choice(PHASES),
        tags=tags if tags else None,
        author_id=author_id,
        parent_id=None,
        root_id=None,
    )


def _make_reply(
    author_id: uuid.UUID,
    parent: MessageModel,
    root: MessageModel,
    now: datetime,
) -> MessageModel:
    tags = random.sample(TAGS_POOL, k=random.randint(0, 2)) or None
    return MessageModel(
        external_id=str(uuid.uuid4()),
        content_type="reply",
        text=fake.paragraph(nb_sentences=random.randint(1, 4)),
        source_created_at=_source_created_at(now),
        edito_id=parent.edito_id,
        topic_id=parent.topic_id,
        phase=parent.phase,
        tags=tags if tags else None,
        author_id=author_id,
        parent_id=parent.id,
        root_id=root.id,
    )


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

async def seed(n_users: int, messages_per_user: int, thread_ratio: float) -> None:
    now = datetime.now(timezone.utc)
    print(f"Seeding {n_users} users × ~{messages_per_user} messages (thread_ratio={thread_ratio}) …")

    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session):
            all_users: list[UserModel] = []
            all_root_messages: list[MessageModel] = []

            # --- Users ---
            for _ in range(n_users):
                user = _make_user()
                session.add(user)
                all_users.append(user)

            await session.flush()
            print(f"  ✓ {n_users} users créés")

            # --- Messages & évaluations ---
            total_messages = 0
            total_evals = 0

            for user in all_users:
                n_msg = random.randint(max(1, messages_per_user - 5), messages_per_user + 5)

                for _ in range(n_msg):
                    use_thread = all_root_messages and random.random() < thread_ratio

                    if use_thread:
                        root = random.choice(all_root_messages)
                        # choisir un parent dans le thread (root ou reply déjà créé)
                        parent = root
                        msg = _make_reply(
                            author_id=user.id,
                            parent=parent,
                            root=root,
                            now=now,
                        )
                    else:
                        msg = _make_root_message(author_id=user.id, now=now)

                    session.add(msg)
                    await session.flush()
                    total_messages += 1

                    if not use_thread:
                        all_root_messages.append(msg)

                    # Évaluation (pas forcément sur chaque message)
                    if random.random() < 0.85:
                        evaluation = _make_evaluation(message_id=msg.id)
                        session.add(evaluation)
                        await session.flush()
                        total_evals += 1

            print(f"  ✓ {total_messages} messages créés")
            print(f"  ✓ {total_evals} évaluations créées")

    print("Seed terminé.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the Nyaya database with fake data.")
    parser.add_argument("--users", type=int, default=15, help="Nombre d'users (défaut: 15)")
    parser.add_argument("--messages", type=int, default=20, help="Messages par user en moyenne (défaut: 20)")
    parser.add_argument("--thread-ratio", type=float, default=0.35, help="Ratio de réponses dans des threads existants (défaut: 0.35)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(seed(
        n_users=args.users,
        messages_per_user=args.messages,
        thread_ratio=args.thread_ratio,
    ))
