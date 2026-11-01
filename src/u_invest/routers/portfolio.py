from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_user
from ..models.portfolio import (
    DemoWallet,
    PortfolioPosition,
    PortfolioTransaction,
    UserProfile,
)
from ..schemas.portfolio import (
    DemoDepositRequest,
    DemoTradeRequest,
    PortfolioPositionResponse,
    PortfolioResponse,
    PortfolioTransactionResponse,
    UserProfileResponse,
)

router = APIRouter(tags=["user portfolio"])
CENT = Decimal("0.01")
MAX_BALANCE = Decimal("9999999999999999.99")
MAX_QUANTITY = Decimal("999999999999.999999")


def require_user_id(
    claims: dict[str, object] = Depends(require_user),
) -> UUID:
    return UUID(str(claims["sub"]))


@router.get("/profile", response_model=UserProfileResponse)
def read_profile(
    claims: dict[str, object] = Depends(require_user),
    session: Session = Depends(get_db),
) -> UserProfileResponse:
    user_id = UUID(str(claims["sub"]))
    profile, _wallet = _ensure_account(session, user_id, claims)
    return UserProfileResponse.model_validate(profile)


@router.get("/portfolio", response_model=PortfolioResponse)
def read_portfolio(
    user_id: UUID = Depends(require_user_id),
    session: Session = Depends(get_db),
) -> PortfolioResponse:
    _ensure_account(session, user_id, {})
    wallet = session.get(DemoWallet, user_id)
    positions = session.scalars(
        select(PortfolioPosition)
        .where(PortfolioPosition.user_id == user_id)
        .order_by(PortfolioPosition.ticker)
    ).all()
    portfolio_value = sum(
        (position.invested_amount for position in positions), start=Decimal("0.00")
    )
    return PortfolioResponse(
        balance=wallet.balance,
        portfolio_value=portfolio_value,
        account_value=wallet.balance + portfolio_value,
        positions=[PortfolioPositionResponse.model_validate(item) for item in positions],
    )


@router.get(
    "/portfolio/transactions",
    response_model=list[PortfolioTransactionResponse],
)
def list_transactions(
    user_id: UUID = Depends(require_user_id),
    session: Session = Depends(get_db),
) -> list[PortfolioTransactionResponse]:
    _ensure_account(session, user_id, {})
    transactions = session.scalars(
        select(PortfolioTransaction)
        .where(PortfolioTransaction.user_id == user_id)
        .order_by(PortfolioTransaction.created_at.desc(), PortfolioTransaction.id.desc())
        .limit(100)
    ).all()
    return [PortfolioTransactionResponse.model_validate(item) for item in transactions]


@router.post(
    "/portfolio/demo-deposits",
    response_model=PortfolioTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def deposit_demo_balance(
    payload: DemoDepositRequest,
    user_id: UUID = Depends(require_user_id),
    session: Session = Depends(get_db),
) -> PortfolioTransactionResponse:
    _ensure_account(session, user_id, {})
    existing = _find_transaction(session, user_id, payload.request_id)
    if existing:
        if existing.transaction_type != "deposit" or existing.amount != payload.amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Цей ключ операції вже використано з іншими даними.",
            )
        return PortfolioTransactionResponse.model_validate(existing)
    session.rollback()
    try:
        with session.begin():
            wallet = session.scalar(
                select(DemoWallet)
                .where(DemoWallet.user_id == user_id)
                .with_for_update()
            )
            if wallet is None:
                raise HTTPException(status_code=404, detail="Demo wallet not found.")
            if wallet.balance + payload.amount > MAX_BALANCE:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Сума перевищує максимальний розмір демобалансу.",
                )
            wallet.balance += payload.amount
            transaction = PortfolioTransaction(
                user_id=user_id,
                request_id=payload.request_id,
                transaction_type="deposit",
                amount=payload.amount,
            )
            session.add(transaction)
            session.flush()
    except IntegrityError:
        session.rollback()
        existing = _find_transaction(session, user_id, payload.request_id)
        if existing:
            if (
                existing.transaction_type == "deposit"
                and existing.amount == payload.amount
            ):
                return PortfolioTransactionResponse.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Цей ключ операції вже використано з іншими даними.",
            ) from None
        raise
    return PortfolioTransactionResponse.model_validate(transaction)


@router.post(
    "/portfolio/trades",
    response_model=PortfolioTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def trade_demo_position(
    payload: DemoTradeRequest,
    user_id: UUID = Depends(require_user_id),
    session: Session = Depends(get_db),
) -> PortfolioTransactionResponse:
    _ensure_account(session, user_id, {})
    existing = _find_transaction(session, user_id, payload.request_id)
    if existing:
        if (
            existing.transaction_type != payload.side
            or existing.ticker != payload.ticker
            or existing.quantity != payload.quantity
            or existing.unit_price != payload.unit_price
            or existing.company != payload.company
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Цей ключ операції вже використано з іншими даними.",
            )
        return PortfolioTransactionResponse.model_validate(existing)
    session.rollback()
    gross_amount = (payload.quantity * payload.unit_price).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    if gross_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The demo trade amount must be at least 0.01 USD.",
        )
    if gross_amount > MAX_BALANCE or payload.quantity > MAX_QUANTITY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Демооперація перевищує допустимий числовий діапазон.",
        )
    try:
        with session.begin():
            wallet = session.scalar(
                select(DemoWallet)
                .where(DemoWallet.user_id == user_id)
                .with_for_update()
            )
            if wallet is None:
                raise HTTPException(status_code=404, detail="Demo wallet not found.")
            position = session.scalar(
                select(PortfolioPosition)
                .where(
                    PortfolioPosition.user_id == user_id,
                    PortfolioPosition.ticker == payload.ticker,
                )
                .with_for_update()
            )
            if payload.side == "buy":
                if wallet.balance < gross_amount:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Недостатньо коштів на деморахунку.",
                    )
                wallet.balance -= gross_amount
                if position is None:
                    position = PortfolioPosition(
                        user_id=user_id,
                        ticker=payload.ticker,
                        company=payload.company,
                        quantity=payload.quantity,
                        average_price=payload.unit_price,
                        invested_amount=gross_amount,
                    )
                    session.add(position)
                else:
                    total_quantity = position.quantity + payload.quantity
                    total_invested = position.invested_amount + gross_amount
                    if total_quantity > MAX_QUANTITY or total_invested > MAX_BALANCE:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Демооперація перевищує допустимий розмір позиції.",
                        )
                    position.company = payload.company
                    position.quantity = total_quantity
                    position.invested_amount = total_invested
                    position.average_price = (
                        total_invested / total_quantity
                    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            else:
                if position is None or position.quantity < payload.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Недостатньо акцій для цього демопродажу.",
                    )
                wallet.balance += gross_amount
                if wallet.balance > MAX_BALANCE:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Сума перевищує максимальний розмір демобалансу.",
                    )
                remaining_quantity = position.quantity - payload.quantity
                if remaining_quantity == 0:
                    session.delete(position)
                else:
                    remaining_investment = (
                        position.average_price * remaining_quantity
                    ).quantize(CENT, rounding=ROUND_HALF_UP)
                    position.quantity = remaining_quantity
                    position.invested_amount = remaining_investment
                    position.average_price = (
                        remaining_investment / remaining_quantity
                    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            transaction = PortfolioTransaction(
                user_id=user_id,
                request_id=payload.request_id,
                transaction_type=payload.side,
                ticker=payload.ticker,
                company=payload.company,
                amount=gross_amount,
                quantity=payload.quantity,
                unit_price=payload.unit_price,
            )
            session.add(transaction)
            session.flush()
    except IntegrityError:
        session.rollback()
        existing = _find_transaction(session, user_id, payload.request_id)
        if existing:
            if (
                existing.transaction_type == payload.side
                and existing.ticker == payload.ticker
                and existing.quantity == payload.quantity
                and existing.unit_price == payload.unit_price
                and existing.company == payload.company
            ):
                return PortfolioTransactionResponse.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Цей ключ операції вже використано з іншими даними.",
            ) from None
        raise
    return PortfolioTransactionResponse.model_validate(transaction)


def _ensure_account(
    session: Session, user_id: UUID, claims: dict[str, object]
) -> tuple[UserProfile, DemoWallet]:
    values = {
        "id": user_id,
        "email": claims.get("email") if isinstance(claims.get("email"), str) else None,
        "display_name": _display_name(claims),
        "created_at": datetime.now(UTC),
    }
    dialect = session.get_bind().dialect.name
    insert = postgresql_insert if dialect == "postgresql" else sqlite_insert
    session.execute(insert(UserProfile).values(**values).on_conflict_do_nothing())
    session.execute(
        insert(DemoWallet)
        .values(user_id=user_id, balance=Decimal("0.00"))
        .on_conflict_do_nothing()
    )
    session.commit()
    profile = session.get(UserProfile, user_id)
    wallet = session.get(DemoWallet, user_id)
    if profile is None or wallet is None:
        raise HTTPException(status_code=503, detail="Не вдалося створити деморахунок.")
    if values["email"] and profile.email != values["email"]:
        profile.email = values["email"]
    if values["display_name"] and profile.display_name != values["display_name"]:
        profile.display_name = values["display_name"]
    session.commit()
    return profile, wallet


def _display_name(claims: dict[str, object]) -> str | None:
    metadata = claims.get("user_metadata")
    if not isinstance(metadata, dict):
        return None
    for key in ("username", "full_name", "name"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:80]
    return None


def _find_transaction(
    session: Session, user_id: UUID, request_id: UUID
) -> PortfolioTransaction | None:
    return session.scalar(
        select(PortfolioTransaction).where(
            PortfolioTransaction.user_id == user_id,
            PortfolioTransaction.request_id == request_id,
        )
    )
