from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Ticker = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9.-]{0,11}$")]
CompanyName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
PositivePrice = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    display_name: str | None
    created_at: datetime


class PortfolioPositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    company: str
    quantity: Decimal
    average_price: Decimal
    invested_amount: Decimal


class PortfolioResponse(BaseModel):
    balance: Decimal
    portfolio_value: Decimal
    account_value: Decimal
    positions: list[PortfolioPositionResponse]


class PortfolioTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_type: Literal["deposit", "buy", "sell"]
    ticker: str | None
    company: str | None
    amount: Decimal
    quantity: Decimal | None
    unit_price: Decimal | None
    created_at: datetime


class DemoDepositRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    amount: PositiveMoney


class DemoTradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    side: Literal["buy", "sell"]
    ticker: Ticker
    company: CompanyName
    quantity: PositiveQuantity
    unit_price: PositivePrice


class ExchangeRate(BaseModel):
    buy: Decimal
    sale: Decimal


class ExchangeRatesResponse(BaseModel):
    provider: Literal["ПриватБанк"]
    updated_at: datetime
    stale: bool
    rates: dict[Literal["USD", "EUR"], ExchangeRate]
