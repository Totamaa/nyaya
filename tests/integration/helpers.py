"""
Fonctions utilitaires pour insérer des données en DB dans les tests d'intégration.
Chaque fonction prend db_session en premier argument, comme les repositories.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession


async def insert_user(db_session: AsyncSession, external_id: str | None = None):
    from app.modules.users.model import UserModel

    user = UserModel(external_id=external_id or str(uuid.uuid4()))
    db_session.add(user)
    await db_session.flush()
    return user


async def insert_message(
    db_session: AsyncSession,
    user_id,
    text: str = "Un message de test.",
    source_created_at: datetime | None = None,
    external_id: str | None = None,
):
    from app.modules.messages.model import MessageModel

    msg = MessageModel(
        external_id=external_id or str(uuid.uuid4()),
        content_type="comment",
        text=text,
        source_created_at=source_created_at or datetime.now(timezone.utc),
        author_id=user_id,
    )
    db_session.add(msg)
    await db_session.flush()
    return msg


async def insert_evaluation(db_session: AsyncSession, message_id, score: float = 5.0):
    from app.modules.evaluations.model import EvaluationModel

    ev = EvaluationModel(
        message_id=message_id,
        clarte_des_idees=score,
        exactitude_verifiabilite=score,
        pertinence=score,
        logique_coherence=score,
        absence_de_sophismes=score,
        ouverture_d_esprit=score,
        volonte_de_comprendre=score,
        contribution_utile=score,
        respect_collaboration=score,
        score_total=score,
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


async def insert_feedback(
    db_session: AsyncSession,
    user,
    month,
    content: str = "Feedback de test mensuel.",
):
    from app.modules.feedbacks.model import UserMonthlyFeedbackModel

    feedback = UserMonthlyFeedbackModel(
        user_id=user.id,
        user_external_id=user.external_id,
        month=month,
        content=content,
        worst_categories=["clarte_des_idees", "pertinence"],
        generated_at=datetime.now(timezone.utc),
    )
    db_session.add(feedback)
    await db_session.flush()
    return feedback


async def insert_user_totem(
    db_session: AsyncSession,
    user_id,
    month,
    totem_code: str = "global_top_50_pct",
    score_snapshot: float = 7.0,
):
    from sqlalchemy import select

    from app.modules.totems.model import TotemModel
    from app.modules.user_totems.model import UserTotemModel

    result = await db_session.execute(
        select(TotemModel).where(TotemModel.code == totem_code)
    )
    totem = result.scalars().one()

    ut = UserTotemModel(
        user_id=user_id,
        totem_id=totem.id,
        month=month,
        score_snapshot=score_snapshot,
    )
    db_session.add(ut)
    await db_session.flush()
    return ut
