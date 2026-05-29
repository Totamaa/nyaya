from datetime import date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.core.utils.date_lib import month_range
from app.modules.totems.exceptions import InvalidYearMonthFormatException
from app.modules.totems.repository import TotemRepository
from app.modules.totems.schemas import TotemAssignment, TotemResponse
from app.modules.user_totems.model import UserTotemModel
from app.modules.user_totems.repository import UserTotemRepository
from app.modules.user_totems.schemas import UserTotemResponse
from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.repository import UserRepository


class TotemService:

    def __init__(
        self,
        logger: LoggerManager,
        session: AsyncSession,
        request_id: str,
        totem_repository: TotemRepository,
        user_totem_repository: UserTotemRepository,
        user_repository: UserRepository,
    ):
        self.tag = "SERVICE:Totem"
        self.logger = logger
        self.session = session
        self.request_id = request_id
        self.totem_repository = totem_repository
        self.user_totem_repository = user_totem_repository
        self.user_repository = user_repository

    async def get_all(self) -> list[TotemResponse]:
        """Retourne tous les totems disponibles."""
        totems = await self.totem_repository.get_all(db=self.session)
        return [TotemResponse.from_model(t) for t in totems]

    async def assign_monthly_totems(
        self,
        user_id: UUID,
        month: date,
        assignments: list[TotemAssignment],
    ) -> list[UserTotemModel] | None:
        """Persiste les totems pré-calculés pour un user sur un mois donné. Idempotent : retourne None si déjà assignés."""
        existing = await self.user_totem_repository.get_by_user_month(
            user_id=user_id, month=month, db=self.session
        )
        if existing:
            self.logger.info(
                tag=self.tag,
                message=f"Totems already assigned for user_id={user_id} month={month}, skipping.",
                extra=self.request_id,
            )
            return None

        if not assignments:
            self.logger.info(
                tag=self.tag,
                message=f"No totems to assign for user_id={user_id} month={month}",
                extra=self.request_id,
            )
            return []

        totems = await self.totem_repository.get_by_codes(
            codes=[a.totem_code for a in assignments],
            db=self.session,
        )
        totem_by_code = {t.code: t for t in totems}

        created: list[UserTotemModel] = []
        for assignment in assignments:
            totem = totem_by_code.get(assignment.totem_code)
            if totem is None:
                self.logger.warning(
                    tag=self.tag,
                    message=f"Totem code '{assignment.totem_code}' not found in DB, skipping.",
                    extra=self.request_id,
                )
                continue
            user_totem = await self.user_totem_repository.create(
                user_totem=UserTotemModel(
                    user_id=user_id,
                    totem_id=totem.id,
                    month=month,
                    score_snapshot=assignment.score_snapshot,
                ),
                db=self.session,
            )
            created.append(user_totem)

        self.logger.info(
            tag=self.tag,
            message=f"Assigned {len(created)} totem(s) to user_id={user_id} month={month}",
            extra=self.request_id,
        )
        return created

    async def get_by_user_and_month(
        self,
        user_external_id: str,
        year_month: str,
    ) -> list[UserTotemResponse]:
        """Retourne les totems d'un user pour un mois précis (format: 'YYYY-MM')."""
        user = await self.user_repository.get_by_external_id(
            external_id=user_external_id,
            db=self.session,
        )
        if not user:
            raise UserNotFoundException(external_id=user_external_id)

        try:
            parsed = datetime.strptime(year_month, "%Y-%m")
            month = date(parsed.year, parsed.month, 1)
        except ValueError:
            raise InvalidYearMonthFormatException(year_month=year_month)

        user_totems = await self.user_totem_repository.get_by_user_month(
            user_id=user.id,
            month=month,
            db=self.session,
        )
        return [UserTotemResponse.from_model(ut) for ut in user_totems]

    async def get_history_by_user(
        self,
        user_external_id: str,
        limit: int,
        offset: int,
    ) -> list[UserTotemResponse]:
        """Retourne les totems d'un user sur une plage de mois (du plus récent au plus ancien)."""
        user = await self.user_repository.get_by_external_id(
            external_id=user_external_id,
            db=self.session,
        )
        if not user:
            raise UserNotFoundException(external_id=user_external_id)

        start_month, end_month = month_range(limit, offset)
        user_totems = await self.user_totem_repository.get_by_user_and_month_range(
            user_id=user.id,
            start_month=start_month,
            end_month=end_month,
            db=self.session,
        )
        return [UserTotemResponse.from_model(ut) for ut in user_totems]
