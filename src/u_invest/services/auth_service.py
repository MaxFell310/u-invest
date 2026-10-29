from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient


@lru_cache(maxsize=4)
def _jwks_client(issuer_url: str) -> PyJWKClient:
    return PyJWKClient(
        f"{issuer_url}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
    )


def verify_supabase_access_token(token: str, supabase_url: str) -> dict[str, Any]:
    issuer = f"{supabase_url.rstrip('/')}/auth/v1"
    signing_key = _jwks_client(supabase_url).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=issuer,
    )
    return claims
