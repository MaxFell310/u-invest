from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from u_invest import dependencies

USER_A = "123e4567-e89b-42d3-a456-426614174001"
USER_B = "123e4567-e89b-42d3-a456-426614174002"


@pytest.fixture
def authenticated_client(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    monkeypatch.setenv("SUPABASE_URL", "https://u-invest-test.supabase.co")
    monkeypatch.delenv("U_INVEST_ADMIN_USER_IDS", raising=False)

    def fake_verify(token: str, _issuer: str) -> dict[str, str]:
        if token not in {"user-a", "user-b"}:
            raise jwt.InvalidTokenError("invalid test token")
        return {
            "sub": USER_A if token == "user-a" else USER_B,
            "email": f"{token}@example.test",
            "user_metadata": {"username": token},
        }

    monkeypatch.setattr(dependencies, "verify_supabase_access_token", fake_verify)
    return client


def headers(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user}"}


def test_portfolio_requires_a_valid_supabase_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://u-invest-test.supabase.co")
    assert client.get("/api/profile").status_code == 401
    response = client.get(
        "/api/portfolio",
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == 401


def test_users_only_read_and_change_their_own_demo_portfolio(
    authenticated_client: TestClient,
) -> None:
    client = authenticated_client
    user_a = headers("user-a")
    user_b = headers("user-b")
    deposit_id = str(uuid4())

    profile = client.get("/api/profile", headers=user_a)
    forged_owner = client.post(
        "/api/portfolio/demo-deposits",
        headers=user_a,
        json={"request_id": deposit_id, "amount": "100.00", "user_id": USER_B},
    )
    deposit = client.post(
        "/api/portfolio/demo-deposits",
        headers=user_a,
        json={"request_id": deposit_id, "amount": "100.00"},
    )
    purchase = client.post(
        "/api/portfolio/trades",
        headers=user_a,
        json={
            "request_id": str(uuid4()),
            "side": "buy",
            "ticker": "AAPL",
            "company": "Apple Inc.",
            "quantity": "2",
            "unit_price": "10.50",
        },
    )
    sale = client.post(
        "/api/portfolio/trades",
        headers=user_a,
        json={
            "request_id": str(uuid4()),
            "side": "sell",
            "ticker": "AAPL",
            "company": "Apple Inc.",
            "quantity": "0.5",
            "unit_price": "11.00",
        },
    )
    portfolio_a = client.get(
        f"/api/portfolio?user_id={USER_B}", headers=user_a
    )
    portfolio_b = client.get("/api/portfolio", headers=user_b)
    transactions_b = client.get("/api/portfolio/transactions", headers=user_b)

    assert profile.status_code == 200
    assert profile.json()["id"] == USER_A
    assert profile.json()["email"] == "user-a@example.test"
    assert forged_owner.status_code == 422
    assert deposit.status_code == 201
    assert purchase.status_code == 201
    assert sale.status_code == 201
    assert portfolio_a.json()["balance"] == "84.50"
    assert portfolio_a.json()["positions"] == [
        {
            "ticker": "AAPL",
            "company": "Apple Inc.",
            "quantity": "1.500000",
            "average_price": "10.500000",
            "invested_amount": "15.75",
        }
    ]
    assert portfolio_b.json()["balance"] == "0.00"
    assert portfolio_b.json()["positions"] == []
    assert transactions_b.json() == []
    assert portfolio_a.json()["account_value"] == "100.25"


def test_demo_operations_are_idempotent_and_reject_insufficient_funds_or_shares(
    authenticated_client: TestClient,
) -> None:
    client = authenticated_client
    auth = headers("user-a")
    request_id = str(uuid4())
    payload = {"request_id": request_id, "amount": "30.00"}
    first = client.post(
        "/api/portfolio/demo-deposits", headers=auth, json=payload
    )
    repeated = client.post(
        "/api/portfolio/demo-deposits", headers=auth, json=payload
    )
    conflicting_replay = client.post(
        "/api/portfolio/demo-deposits",
        headers=auth,
        json={"request_id": request_id, "amount": "50.00"},
    )
    insufficient_buy = client.post(
        "/api/portfolio/trades",
        headers=auth,
        json={
            "request_id": str(uuid4()),
            "side": "buy",
            "ticker": "TSLA",
            "company": "Tesla",
            "quantity": "10",
            "unit_price": "10",
        },
    )
    missing_shares = client.post(
        "/api/portfolio/trades",
        headers=auth,
        json={
            "request_id": str(uuid4()),
            "side": "sell",
            "ticker": "TSLA",
            "company": "Tesla",
            "quantity": "1",
            "unit_price": "10",
        },
    )

    assert first.status_code == repeated.status_code == 201
    assert first.json()["id"] == repeated.json()["id"]
    assert conflicting_replay.status_code == 409
    assert insufficient_buy.status_code == 409
    assert missing_shares.status_code == 409
    assert client.get("/api/portfolio", headers=auth).json()["balance"] == "30.00"
    assert len(client.get("/api/portfolio/transactions", headers=auth).json()) == 1


def test_public_signup_does_not_authorize_private_admin_endpoints(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get(
        "/api/admin/feedback", headers=headers("user-a")
    )
    assert response.status_code == 403
