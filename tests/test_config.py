import pytest
from sqlalchemy.engine import make_url

from u_invest.config import database_url


def test_production_database_url_uses_psycopg_and_requires_ssl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("U_INVEST_ENV", "production")
    monkeypatch.setenv(
        "U_INVEST_DATABASE_URL",
        "postgresql://u-invest:placeholder@db.example.test:5432/investments",
    )

    parsed_url = make_url(database_url())

    assert parsed_url.drivername == "postgresql+psycopg"
    assert parsed_url.password == "placeholder"
    assert parsed_url.query["sslmode"] == "require"


def test_production_rejects_sqlite_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("U_INVEST_ENV", "production")
    monkeypatch.setenv("U_INVEST_DATABASE_URL", "sqlite:///./local.db")

    with pytest.raises(ValueError, match="Production deployments must use PostgreSQL"):
        database_url()
