from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json

from fastapi.testclient import TestClient

from u_invest.routers import exchange_rates
from u_invest.schemas.portfolio import ExchangeRate


def valid_rates() -> dict[str, ExchangeRate]:
    return {
        "USD": ExchangeRate(buy=Decimal("41.10"), sale=Decimal("41.60")),
        "EUR": ExchangeRate(buy=Decimal("44.20"), sale=Decimal("44.90")),
    }


def test_exchange_endpoint_returns_normalized_provider_rates(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(exchange_rates, "_cached_rates", None)
    monkeypatch.setattr(exchange_rates, "_fetch_rates", valid_rates)

    response = client.get("/api/exchange-rates")

    assert response.status_code == 200
    assert response.json()["provider"] == "ПриватБанк"
    assert response.json()["rates"]["USD"] == {"buy": "41.10", "sale": "41.60"}
    assert response.json()["rates"]["EUR"] == {"buy": "44.20", "sale": "44.90"}
    assert response.json()["stale"] is False


def test_exchange_endpoint_uses_stale_cache_when_provider_is_unavailable(
    client: TestClient, monkeypatch
) -> None:
    cached = exchange_rates.ExchangeRatesResponse(
        provider="ПриватБанк",
        updated_at=datetime.now(UTC) - timedelta(minutes=30),
        stale=False,
        rates=valid_rates(),
    )
    monkeypatch.setattr(exchange_rates, "_cached_rates", cached)
    monkeypatch.setattr(
        exchange_rates,
        "_fetch_rates",
        lambda: (_ for _ in ()).throw(OSError("provider unavailable")),
    )

    response = client.get("/api/exchange-rates")

    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert response.json()["updated_at"] == cached.updated_at.isoformat().replace("+00:00", "Z")


def test_exchange_endpoint_reports_unavailable_without_cached_data(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(exchange_rates, "_cached_rates", None)
    monkeypatch.setattr(
        exchange_rates,
        "_fetch_rates",
        lambda: (_ for _ in ()).throw(OSError("provider unavailable")),
    )

    response = client.get("/api/exchange-rates")

    assert response.status_code == 503
    assert response.json()["detail"] == "Курс валют тимчасово недоступний."


def test_fresh_exchange_cache_prevents_another_provider_request(
    client: TestClient, monkeypatch
) -> None:
    cached = exchange_rates.ExchangeRatesResponse(
        provider="ПриватБанк",
        updated_at=datetime.now(UTC),
        stale=False,
        rates=valid_rates(),
    )
    monkeypatch.setattr(exchange_rates, "_cached_rates", cached)

    def unexpected_request():
        raise AssertionError("fresh cache should avoid provider request")

    monkeypatch.setattr(exchange_rates, "_fetch_rates", unexpected_request)

    response = client.get("/api/exchange-rates")

    assert response.status_code == 200
    assert response.json()["stale"] is False


def test_provider_parser_filters_to_ua_base_usd_and_eur(monkeypatch) -> None:
    payload = [
        {"ccy": "USD", "base_ccy": "UAH", "buy": "41.10", "sale": "41.60"},
        {"ccy": "EUR", "base_ccy": "UAH", "buy": "44.20", "sale": "44.90"},
        {"ccy": "BTC", "base_ccy": "USD", "buy": "1", "sale": "2"},
    ]

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    def fake_urlopen(url, timeout):
        assert url == exchange_rates.PRIVATBANK_URL
        assert timeout == 5
        return FakeResponse()

    monkeypatch.setattr(exchange_rates, "urlopen", fake_urlopen)

    parsed = exchange_rates._fetch_rates()

    assert set(parsed) == {"USD", "EUR"}
    assert parsed["USD"].buy == Decimal("41.10")
