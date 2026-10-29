from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from ..models import Base
from ..schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API and database health",
    description="Executes a lightweight database query and reports service availability.",
    responses={503: {"description": "The configured database is unavailable."}},
)
def health_check(request: Request) -> HealthResponse:
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            existing_tables = set(inspect(connection).get_table_names())
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503, detail="Database is unavailable."
        ) from error
    missing_tables = set(Base.metadata.tables) - existing_tables
    if missing_tables:
        raise HTTPException(
            status_code=503,
            detail=(
                "Database schema is not initialized. "
                "Run `uv run alembic upgrade head`."
            ),
        )
    return HealthResponse(status="ok")
