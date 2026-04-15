from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.config.settings import get_settings
from app.core.config.logs import get_logger
from app.core.errors.exceptions.base import AppException
from app.core.errors.handlers.business import handle_business_exceptions
from app.core.errors.handlers.catchall import handle_generic_exceptions
from app.core.errors.handlers.db import handle_db_exceptions
from app.core.middleware.headers import add_global_headers
from app.core.api.router import router_api
from app.jobs.scheduled.scheduler import start_scheduler, stop_scheduler

def create_app() -> FastAPI:
    
    logger = get_logger()
    settings = get_settings()
    
    docs_url = redoc_url = openapi_url = None
    
    if settings.ENVIRONMENT != "prod":
        docs_url = "/api/docs"
        redoc_url = "/api/redoc"
        openapi_url = "/api/openapi.json"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("SYSTEM:Startup", "Backend started")
        start_scheduler()
        yield
        stop_scheduler()
        logger.info("SYSTEM:Shutdown", "Backend stopped")

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
        }
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,  # ex: ["*"] or ["https://frontend.com"]
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.middleware("http")(add_global_headers)
    
    app.add_exception_handler(AppException, handle_business_exceptions)
    app.add_exception_handler(SQLAlchemyError, handle_db_exceptions)
    app.add_exception_handler(Exception, handle_generic_exceptions)
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    app.include_router(router_api, prefix="/api")

    return app

app = create_app()
