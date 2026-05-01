"""
Seed script — remplit la BD avec des données réalistes via Faker.

Usage (depuis la racine du projet) :
    python scripts/seed.py
    python scripts/seed.py --users 100 --messages 50 --thread-ratio 0.3 --batch 1000

Architecture :
  1. Toute la data est construite en mémoire (Python pur, IDs pré-générés côté client).
  2. Insertions en 4 phases séquentielles qui respectent les FK,
     chaque phase étant parallélisée via asyncio.gather (une session/commit par batch).

  users → root messages → replies → evaluations
"""
import argparse
import asyncio
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.core.config.database import DATABASE_URL, UnitOfWork
from app.modules.evaluations.model import EvaluationModel
from app.modules.messages.model import MessageModel
from app.modules.users.model import UserModel

_engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

fake = Faker("fr_FR")

CONTENT_TYPES = ["comment", "reply", "post"]
PHASES = ["deliberation", "consultation", "vote", None]
TAGS_POOL = [
    "economie", "sante", "education", "environnement", "justice",
    "logement", "transport", "culture", "numerique", "securite",
]
LAST_MONTH_RATIO = 0.80


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def _bulk_insert(rows: list) -> None:
    async with _Session() as session:
        async with UnitOfWork(session):
            session.add_all(rows)
            await session.flush()


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
        id=uuid.uuid4(),
        message_id=message_id,
        likes=random.randint(0, 150),
        score_total=score_total,
        **scores,
    )


def _source_created_at(now: datetime) -> datetime:
    if random.random() < LAST_MONTH_RATIO:
        first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 1:
            first_of_prev = first_of_current.replace(year=now.year - 1, month=12)
        else:
            first_of_prev = first_of_current.replace(month=now.month - 1)
        delta = (first_of_current - first_of_prev).total_seconds()
        return first_of_prev + timedelta(seconds=random.uniform(0, delta))
    else:
        offset_days = random.choice([
            random.randint(0, max(0, now.day - 1)),
            random.randint(32, 120),
        ])
        return now - timedelta(days=offset_days, seconds=random.randint(0, 86400))


def _make_user() -> UserModel:
    # ID pré-généré côté client pour être disponible immédiatement en mémoire
    return UserModel(id=uuid.uuid4(), external_id=str(uuid.uuid4()))


def _make_root_message(author_id: uuid.UUID, now: datetime) -> MessageModel:
    tags = random.sample(TAGS_POOL, k=random.randint(0, 3)) or None
    return MessageModel(
        id=uuid.uuid4(),
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
        id=uuid.uuid4(),
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

async def seed(
    n_users: int,
    messages_per_user: int,
    thread_ratio: float,
    batch_size: int,
) -> None:
    now = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    print(f"  building {n_users} users × ~{messages_per_user} msgs in memory...", end=" ", flush=True)

    users: list[UserModel] = [_make_user() for _ in range(n_users)]
    root_messages: list[MessageModel] = []
    reply_messages: list[MessageModel] = []
    evaluations: list[EvaluationModel] = []

    for user in users:
        n_msg = random.randint(max(1, messages_per_user - 5), messages_per_user + 5)
        for _ in range(n_msg):
            use_thread = bool(root_messages) and random.random() < thread_ratio
            if use_thread:
                root = random.choice(root_messages)
                msg = _make_reply(author_id=user.id, parent=root, root=root, now=now)
                reply_messages.append(msg)
            else:
                msg = _make_root_message(author_id=user.id, now=now)
                root_messages.append(msg)
            if random.random() < 0.85:
                evaluations.append(_make_evaluation(message_id=msg.id))

    n_messages = len(root_messages) + len(reply_messages)
    print(f"done  ({n_users} users, {n_messages} msgs, {len(evaluations)} evals)  {time.perf_counter() - t0:.2f}s")

    async def phase(label: str, rows: list) -> None:
        if not rows:
            return
        batches = list(_chunks(rows, batch_size))
        t = time.perf_counter()
        print(f"  {label:<16}  {len(rows):>6} rows  {len(batches):>3} batch(es)...", end=" ", flush=True)
        await asyncio.gather(*[_bulk_insert(b) for b in batches])
        print(f"{time.perf_counter() - t:.2f}s")

    await phase("users",         users)
    await phase("root messages", root_messages)
    await phase("replies",       reply_messages)
    await phase("evaluations",   evaluations)

    print(f"\n  done in {time.perf_counter() - t0:.2f}s")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the Nyaya database with fake data.")
    parser.add_argument("--users", type=int, default=15, help="Nombre d'users (défaut: 15)")
    parser.add_argument("--messages", type=int, default=20, help="Messages par user en moyenne (défaut: 20)")
    parser.add_argument("--thread-ratio", type=float, default=0.35, help="Ratio de réponses dans des threads existants (défaut: 0.35)")
    parser.add_argument("--batch", type=int, default=500, help="Lignes par batch/session (défaut: 500)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(seed(
        n_users=args.users,
        messages_per_user=args.messages,
        thread_ratio=args.thread_ratio,
        batch_size=args.batch,
    ))
