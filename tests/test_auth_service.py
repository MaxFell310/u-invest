from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from u_invest.services import auth_service


class FakeSigningKeyClient:
    def __init__(self, public_key: rsa.RSAPublicKey) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, _token: str) -> Any:
        return type("SigningKey", (), {"key": self.public_key})()


def test_verifies_supabase_issuer_audience_and_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issuer_url = "https://u-invest-test.supabase.co"
    issuer = f"{issuer_url}/auth/v1"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        auth_service,
        "_jwks_client",
        lambda _issuer_url: FakeSigningKeyClient(key.public_key()),
    )
    token = jwt.encode(
        {
            "sub": "123e4567-e89b-42d3-a456-426614174000",
            "aud": "authenticated",
            "iss": issuer,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    claims = auth_service.verify_supabase_access_token(token, issuer_url)

    assert claims["sub"] == "123e4567-e89b-42d3-a456-426614174000"


def test_rejects_token_from_wrong_issuer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issuer_url = "https://u-invest-test.supabase.co"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        auth_service,
        "_jwks_client",
        lambda _issuer_url: FakeSigningKeyClient(key.public_key()),
    )
    token = jwt.encode(
        {
            "sub": "123e4567-e89b-42d3-a456-426614174000",
            "aud": "authenticated",
            "iss": "https://attacker.example/auth/v1",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(jwt.InvalidIssuerError):
        auth_service.verify_supabase_access_token(token, issuer_url)
