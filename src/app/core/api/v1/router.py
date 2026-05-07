from fastapi import APIRouter, Depends

from app.core.api.dependencies.auth import verify_api_key
from app.core.api.v1.evaluations import router as evaluations_router
from app.core.api.v1.messages import router as messages_router
from app.core.api.v1.totems import router as totems_router
from app.core.api.v1.users import router as users_router

router_v1 = APIRouter(dependencies=[Depends(verify_api_key)])

router_v1.include_router(messages_router, prefix="/messages", tags=["Messages"])
router_v1.include_router(evaluations_router, prefix="/evaluations", tags=["Evaluations"])
router_v1.include_router(totems_router, prefix="/totems", tags=["Totems"])
router_v1.include_router(users_router, prefix="/users", tags=["Users"])
