from fastapi import APIRouter

from app.core.api.v1.messages import router as messages_router

router_v1 = APIRouter()

router_v1.include_router(messages_router, prefix="/messages", tags=["Messages"])
