from fastapi import APIRouter

from app.core.api.v1.evaluations import router as evaluations_router
from app.core.api.v1.feedbacks import router as feedbacks_router
from app.core.api.v1.messages import router as messages_router
from app.core.api.v1.users import router as users_router

router_v1 = APIRouter()

router_v1.include_router(messages_router, prefix="/messages", tags=["Messages"])
router_v1.include_router(evaluations_router, prefix="/evaluations", tags=["Evaluations"])
router_v1.include_router(feedbacks_router, prefix="/users", tags=["Feedbacks"])
router_v1.include_router(users_router, prefix="/users", tags=["Users"])
