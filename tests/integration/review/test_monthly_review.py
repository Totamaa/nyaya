"""
Tests d'intégration pour la pipeline de review mensuelle.

Stratégie :
- Les services sont instanciés directement avec la session de test (pas de broker TaskIQ).
- Les données sont insérées en DB via les helpers (pas de POST /messages) pour éviter
  les appels LLM superflus. Seul test_feedback_generated_for_eligible_user provoque
  un appel au stub LLM (une seule fois, pour valider le chemin complet).
- Les messages doivent avoir source_created_at dans le MOIS PRÉCÉDENT, puisque la
  review porte toujours sur la période N-1.
"""
import uuid
from datetime import date, datetime, timezone

import pytest

from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.service import EvaluationService
from app.modules.feedbacks.exceptions import InsufficientDataForFeedbackException
from app.modules.feedbacks.repository import FeedbackRepository
from app.modules.feedbacks.service import FeedbackService
from app.modules.messages.repository import MessageRepository
from app.modules.totems.repository import TotemRepository
from app.modules.totems.schemas import TotemAssignment
from app.modules.totems.service import TotemService
from app.modules.totems.utils import CRITERIA, compute_totem_assignments
from app.modules.user_totems.repository import UserTotemRepository
from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from tests.integration.helpers import (
    insert_evaluation,
    insert_feedback,
    insert_message,
    insert_user,
    insert_user_totem,
)


def _prev_month_period() -> tuple[datetime, datetime, date]:
    """Retourne (period_start, period_end, month) pour le mois précédent."""
    now = datetime.now(timezone.utc)
    period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        period_start = period_end.replace(year=now.year - 1, month=12)
    else:
        period_start = period_end.replace(month=now.month - 1)
    month = date(period_start.year, period_start.month, 1)
    return period_start, period_end, month


def _user_service(db_session, app_logger) -> UserService:
    return UserService(
        logger=app_logger,
        session=db_session,
        request_id="test:review",
        user_repository=UserRepository(),
        message_repository=MessageRepository(),
    )


def _eval_service(db_session, app_logger) -> EvaluationService:
    return EvaluationService(
        logger=app_logger,
        session=db_session,
        request_id="test:review",
        evaluation_repository=EvaluationRepository(),
    )


def _feedback_service(db_session, app_logger) -> FeedbackService:
    return FeedbackService(
        logger=app_logger,
        session=db_session,
        request_id="test:review",
        feedback_repository=FeedbackRepository(),
        message_repository=MessageRepository(),
        user_repository=UserRepository(),
    )


def _totem_service(db_session, app_logger) -> TotemService:
    return TotemService(
        logger=app_logger,
        session=db_session,
        request_id="test:review",
        totem_repository=TotemRepository(),
        user_totem_repository=UserTotemRepository(),
        user_repository=UserRepository(),
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Éligibilité
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestEligibility:

    async def test_user_with_enough_messages_is_eligible(self, db_session, app_logger, settings):
        period_start, _, _ = _prev_month_period()
        mid_last_month = period_start.replace(day=15)

        user = await insert_user(db_session, "eligible-user")
        for _ in range(settings.REVIEW_MIN_MESSAGES):
            await insert_message(db_session, user.id, source_created_at=mid_last_month)

        eligible_ids = await _user_service(db_session, app_logger).get_eligible_user_ids_for_monthly_review()

        assert user.id in eligible_ids

    async def test_user_with_too_few_messages_is_not_eligible(self, db_session, app_logger, settings):
        period_start, _, _ = _prev_month_period()
        mid_last_month = period_start.replace(day=15)

        user = await insert_user(db_session, "ineligible-few")
        for _ in range(max(0, settings.REVIEW_MIN_MESSAGES - 1)):
            await insert_message(db_session, user.id, source_created_at=mid_last_month)

        eligible_ids = await _user_service(db_session, app_logger).get_eligible_user_ids_for_monthly_review()

        assert user.id not in eligible_ids

    async def test_user_with_no_messages_is_not_eligible(self, db_session, app_logger):
        user = await insert_user(db_session, "ineligible-none")

        eligible_ids = await _user_service(db_session, app_logger).get_eligible_user_ids_for_monthly_review()

        assert user.id not in eligible_ids

    async def test_messages_from_current_month_do_not_count(self, db_session, app_logger, settings):
        """Les messages du mois en cours ne comptent pas pour la review N-1."""
        now = datetime.now(timezone.utc)

        user = await insert_user(db_session, "ineligible-current-month")
        for _ in range(settings.REVIEW_MIN_MESSAGES):
            await insert_message(db_session, user.id, source_created_at=now)

        eligible_ids = await _user_service(db_session, app_logger).get_eligible_user_ids_for_monthly_review()

        assert user.id not in eligible_ids


# ──────────────────────────────────────────────────────────────────────────────
#  Génération de feedback
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.ai
class TestFeedbackGeneration:

    async def test_generates_feedback_for_eligible_user(self, db_session, app_logger, settings):
        """Appel au stub LLM une seule fois — valide le chemin complet."""
        period_start, period_end, month = _prev_month_period()
        mid_last_month = period_start.replace(day=15)

        user = await insert_user(db_session, "feedback-gen-ok")
        for i in range(settings.REVIEW_MIN_MESSAGES):
            msg = await insert_message(
                db_session, user.id,
                text=f"Argument {i} bien construit.",
                source_created_at=mid_last_month,
            )
            await insert_evaluation(db_session, msg.id, score=float(4 + i % 6))

        result = await _feedback_service(db_session, app_logger).generate(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
        )

        assert result.content is not None
        assert result.month == month
        assert result.worst_categories is not None
        assert result.user_id == user.id

    async def test_returns_existing_feedback_without_calling_llm_again(self, db_session, app_logger):
        period_start, period_end, month = _prev_month_period()

        user = await insert_user(db_session, "feedback-gen-idempotent")
        existing = await insert_feedback(db_session, user, month, content="Feedback déjà généré.")

        result = await _feedback_service(db_session, app_logger).generate(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
        )

        assert result.id == existing.id
        assert result.content == "Feedback déjà généré."

    async def test_raises_when_messages_have_no_evaluations(self, db_session, app_logger, settings):
        """Messages sans évaluations → pas de données pour le LLM → exception."""
        period_start, period_end, _ = _prev_month_period()
        mid_last_month = period_start.replace(day=15)

        user = await insert_user(db_session, "feedback-gen-no-eval")
        for _ in range(settings.REVIEW_MIN_MESSAGES):
            await insert_message(db_session, user.id, source_created_at=mid_last_month)

        with pytest.raises(InsufficientDataForFeedbackException):
            await _feedback_service(db_session, app_logger).generate(
                user_id=user.id,
                period_start=period_start,
                period_end=period_end,
            )

    async def test_raises_when_user_does_not_exist(self, db_session, app_logger):
        period_start, period_end, _ = _prev_month_period()

        with pytest.raises(UserNotFoundException):
            await _feedback_service(db_session, app_logger).generate(
                user_id=uuid.uuid4(),
                period_start=period_start,
                period_end=period_end,
            )


# ──────────────────────────────────────────────────────────────────────────────
#  Rankings et calcul des totems
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestRankingsAndAssignments:

    async def test_rankings_order_users_by_score(self, db_session, app_logger):
        top_user = await insert_user(db_session, "ranking-top")
        bottom_user = await insert_user(db_session, "ranking-bottom")

        top_msg = await insert_message(db_session, top_user.id)
        bottom_msg = await insert_message(db_session, bottom_user.id)
        await insert_evaluation(db_session, top_msg.id, score=9.0)
        await insert_evaluation(db_session, bottom_msg.id, score=2.0)

        _, global_ranking = await _eval_service(db_session, app_logger).get_all_rankings(CRITERIA)

        global_ids = [uid for uid, _ in global_ranking]
        assert global_ids.index(top_user.id) < global_ids.index(bottom_user.id)

    async def test_compute_totem_assignments_for_top_user(self, db_session, app_logger):
        """Un user seul dans le ranking est 1er absolu → doit obtenir des totems."""
        user = await insert_user(db_session, "totem-assign-top")
        msg = await insert_message(db_session, user.id)
        await insert_evaluation(db_session, msg.id, score=8.0)

        criteria_rankings, global_ranking = await _eval_service(db_session, app_logger).get_all_rankings(CRITERIA)
        assignments = compute_totem_assignments(user.id, criteria_rankings, global_ranking)

        assert len(assignments) > 0
        assert any("top_1_absolu" in a.totem_code for a in assignments)

    async def test_compute_totem_assignments_for_user_below_threshold(self, db_session, app_logger):
        """Un user en bas du classement (> 50%) ne reçoit aucun totem."""
        for i in range(3):
            u = await insert_user(db_session, f"totem-threshold-{i}")
            msg = await insert_message(db_session, u.id)
            await insert_evaluation(db_session, msg.id, score=9.0 - i * 0.1)

        bottom_user = await insert_user(db_session, "totem-threshold-bottom")
        bottom_msg = await insert_message(db_session, bottom_user.id)
        await insert_evaluation(db_session, bottom_msg.id, score=1.0)

        criteria_rankings, global_ranking = await _eval_service(db_session, app_logger).get_all_rankings(CRITERIA)
        assignments = compute_totem_assignments(bottom_user.id, criteria_rankings, global_ranking)

        assert assignments == []


# ──────────────────────────────────────────────────────────────────────────────
#  Assignation des totems
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestTotemAssignment:

    async def test_assigns_totems_to_user(self, db_session, app_logger):
        _, _, month = _prev_month_period()
        user = await insert_user(db_session, "assign-totems-ok")
        msg = await insert_message(db_session, user.id)
        await insert_evaluation(db_session, msg.id, score=8.0)

        criteria_rankings, global_ranking = await _eval_service(db_session, app_logger).get_all_rankings(CRITERIA)
        assignments = compute_totem_assignments(user.id, criteria_rankings, global_ranking)

        result = await _totem_service(db_session, app_logger).assign_monthly_totems(
            user_id=user.id,
            month=month,
            assignments=assignments,
        )

        assert result is not None
        assert len(result) == len(assignments)

    async def test_assignment_is_idempotent(self, db_session, app_logger):
        """Appeler assign_monthly_totems une 2e fois pour le même mois retourne None."""
        _, _, month = _prev_month_period()
        user = await insert_user(db_session, "assign-totems-idempotent")
        await insert_user_totem(db_session, user.id, month, totem_code="global_top_50_pct")

        result = await _totem_service(db_session, app_logger).assign_monthly_totems(
            user_id=user.id,
            month=month,
            assignments=[TotemAssignment(totem_code="global_top_25_pct", score_snapshot=8.0)],
        )

        assert result is None

    async def test_empty_assignments_persists_nothing(self, db_session, app_logger):
        """Un user sans totem mérité → liste vide persistée, pas d'erreur."""
        _, _, month = _prev_month_period()
        user = await insert_user(db_session, "assign-totems-empty")

        result = await _totem_service(db_session, app_logger).assign_monthly_totems(
            user_id=user.id,
            month=month,
            assignments=[],
        )

        assert result == []
