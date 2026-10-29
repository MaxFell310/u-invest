import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import StaticPool

from .config import database_url


def create_database_engine(url: str) -> Engine:
    parsed_url = make_url(url)
    if parsed_url.drivername.startswith("sqlite"):
        engine_options: dict[str, object] = {
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": True,
        }
    elif parsed_url.drivername == "postgresql+psycopg":
        engine_options = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 5,
            "max_overflow": 2,
        }
        if parsed_url.host and parsed_url.host.endswith(".pooler.supabase.com"):
            engine_options["connect_args"] = {"prepare_threshold": None}
    else:
        raise ValueError(
            "U_INVEST_DATABASE_URL must use SQLite or PostgreSQL with psycopg."
        )

    if parsed_url.drivername.startswith("sqlite") and parsed_url.database in {
        None,
        "",
        ":memory:",
    }:
        engine_options["poolclass"] = StaticPool

    database_engine = create_engine(parsed_url, **engine_options)

    if parsed_url.drivername.startswith("sqlite"):
        @event.listens_for(database_engine, "connect")
        def _enable_sqlite_foreign_keys(
            dbapi_connection: sqlite3.Connection, _connection_record: object
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return database_engine


engine = create_database_engine(database_url())
