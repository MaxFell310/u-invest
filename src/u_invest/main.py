import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import app_host, app_port, cors_origins
from .database import engine
from .routers.admin import router as admin_router
from .routers.analytics import router as analytics_router
from .routers.experiments import router as experiments_router
from .routers.exchange_rates import router as exchange_rates_router
from .routers.feedback import router as feedback_router
from .routers.health import router as health_router
from .routers.portfolio import router as portfolio_router


def create_app(database_engine: Engine = engine) -> FastAPI:
    application = FastAPI(
        title="U-Invest API",
        description="Backend API for the U-Invest MVP experiment and feedback collection.",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.engine = database_engine
    application.state.session_factory = sessionmaker(
        bind=database_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.include_router(health_router, prefix="/api")
    application.include_router(experiments_router, prefix="/api/experiments")
    application.include_router(analytics_router, prefix="/api/analytics")
    application.include_router(feedback_router, prefix="/api")
    application.include_router(exchange_rates_router, prefix="/api")
    application.include_router(portfolio_router, prefix="/api")
    application.include_router(admin_router, prefix="/api/admin")
    return application


app = create_app()


def run() -> None:
    uvicorn.run(
        "u_invest.main:app",
        host=app_host(),
        port=app_port(),
    )
