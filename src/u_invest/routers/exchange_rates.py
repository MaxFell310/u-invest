import json
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, status

from ..schemas.portfolio import ExchangeRate, ExchangeRatesResponse

router = APIRouter(tags=["exchange rates"])
PRIVATBANK_URL = (
    "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5"
)
CACHE_TTL = timedelta(minutes=10)
_cache_lock = threading.Lock()
_cached_rates: ExchangeRatesResponse | None = None


@router.get("/exchange-rates", response_model=ExchangeRatesResponse)
def get_exchange_rates() -> ExchangeRatesResponse:
    global _cached_rates
    now = datetime.now(UTC)
    with _cache_lock:
        cached = _cached_rates
        if cached and now - cached.updated_at < CACHE_TTL:
            return cached
        try:
            rates = _fetch_rates()
        except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            cached = _cached_rates
            if cached:
                return cached.model_copy(update={"stale": True})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Курс валют тимчасово недоступний.",
            )
        result = ExchangeRatesResponse(
            provider="ПриватБанк",
            updated_at=datetime.now(UTC),
            stale=False,
            rates=rates,
        )
        _cached_rates = result
        return result


def _fetch_rates() -> dict[str, ExchangeRate]:
    with urlopen(PRIVATBANK_URL, timeout=5) as response:
        if response.status != 200:
            raise OSError("PrivatBank returned an unsuccessful status.")
        payload = json.loads(response.read())
    if not isinstance(payload, list):
        raise ValueError("Unexpected PrivatBank response.")
    rates: dict[str, ExchangeRate] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        currency = row.get("ccy")
        if currency not in {"USD", "EUR"} or row.get("base_ccy") != "UAH":
            continue
        try:
            buy = Decimal(str(row["buy"]))
            sale = Decimal(str(row["sale"]))
        except (KeyError, InvalidOperation) as error:
            raise ValueError("Invalid PrivatBank rate fields.") from error
        if not buy.is_finite() or not sale.is_finite() or buy <= 0 or sale <= 0:
            raise ValueError("Invalid PrivatBank rates.")
        rates[currency] = ExchangeRate(buy=buy, sale=sale)
    if set(rates) != {"USD", "EUR"}:
        raise ValueError("PrivatBank response is missing USD or EUR rates.")
    return rates
