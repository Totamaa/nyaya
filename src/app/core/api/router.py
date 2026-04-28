from fastapi import APIRouter

from app.core.api.v1.router import router_v1

router_api = APIRouter()

router_api.include_router(router_v1, prefix="/v1")
