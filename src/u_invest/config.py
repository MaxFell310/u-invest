import os

from sqlalchemy.engine import make_url


def database_url() -> str:
    raw_url = os.getenv("U_INVEST_DATABASE_URL", "sqlite:///./u_invest.db")
    if raw_url.startswith("postgres://"):
        raw_url = "postgresql+psycopg://" + raw_url.removeprefix("postgres://")
    elif raw_url.startswith("postgresql://"):
        raw_url = "postgresql+psycopg://" + raw_url.removeprefix("postgresql://")

    parsed_url = make_url(raw_url)
    if parsed_url.drivername == "postgresql+psycopg":
        if os.getenv("U_INVEST_ENV", "development").lower() == "production":
            query = dict(parsed_url.query)
            query.setdefault("sslmode", "require")
            parsed_url = parsed_url.set(query=query)
    elif parsed_url.drivername.startswith("sqlite"):
        if os.getenv("U_INVEST_ENV", "development").lower() == "production":
            raise ValueError("Production deployments must use PostgreSQL.")
    else:
        raise ValueError(
            "U_INVEST_DATABASE_URL must use SQLite or PostgreSQL."
        )

    return parsed_url.render_as_string(hide_password=False)


def cors_origins() -> list[str]:
    configured = os.getenv(
        "U_INVEST_CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def admin_user_ids() -> frozenset[str]:
    configured = os.getenv("U_INVEST_ADMIN_USER_IDS", "")
    return frozenset(
        user_id.strip().lower()
        for user_id in configured.split(",")
        if user_id.strip()
    )


def app_host() -> str:
    return os.getenv("U_INVEST_HOST", "127.0.0.1")


def app_port() -> int:
    return int(os.getenv("U_INVEST_PORT", "8000"))
