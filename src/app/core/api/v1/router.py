from fastapi import APIRouter

from app.core.api.v1.evaluations import router as evaluations_router
from app.core.api.v1.messages import router as messages_router

router_v1 = APIRouter()

router_v1.include_router(messages_router, prefix="/messages", tags=["Messages"])
router_v1.include_router(evaluations_router, prefix="/evaluations", tags=["Evaluations"])
