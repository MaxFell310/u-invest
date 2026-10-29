import csv
from io import StringIO
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from u_invest import dependencies

ADMIN_ID = str(uuid4())
OTHER_ID = str(uuid4())


def enable_test_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://u-invest-test.supabase.co")
    monkeypatch.setenv("U_INVEST_ADMIN_USER_IDS", ADMIN_ID)

    def fake_verify(token: str, _issuer: str) -> dict[str, str]:
        if token == "invalid":
            raise jwt.InvalidTokenError("invalid test token")
        return {"sub": OTHER_ID if token == "other" else ADMIN_ID}

    monkeypatch.setattr(dependencies, "verify_supabase_access_token", fake_verify)


def feedback_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rating": 4,
        "investment_interest": "yes",
        "comment": "Interested in learning more.",
        "environmental_importance": "very_important",
        "social_importance": "moderately_important",
        "ethical_importance": "very_important",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/feedback",
        "/api/admin/feedback/summary",
        "/api/admin/feedback/export",
        "/api/analytics/export",
    ],
)
def test_private_feedback_endpoints_require_authentication(
    client: TestClient, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 401


def test_invalid_or_non_allowlisted_token_cannot_read_feedback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    enable_test_auth(monkeypatch)

    invalid = client.get(
        "/api/admin/feedback",
        headers={"Authorization": "Bearer invalid"},
    )
    unauthorized_user = client.get(
        "/api/admin/feedback",
        headers={"Authorization": "Bearer other"},
    )

    assert invalid.status_code == 401
    assert unauthorized_user.status_code == 403


def test_authorized_collaborator_can_filter_view_and_export_feedback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    enable_test_auth(monkeypatch)
    submitted = client.post(
        "/api/feedback",
        json=feedback_payload(
            comment='=HYPERLINK("https://example.invalid","comment")'
        ),
    )
    assert submitted.status_code == 201
    headers = {"Authorization": "Bearer admin"}

    page = client.get(
        "/api/admin/feedback?q=HYPERLINK&rating=4",
        headers=headers,
    )
    summary = client.get("/api/admin/feedback/summary", headers=headers)
    export = client.get("/api/admin/feedback/export", headers=headers)

    assert page.status_code == 200
    assert page.json()["total"] == 1
    item = page.json()["items"][0]
    assert item["rating"] == 4
    assert item["investment_interest"] == "yes"
    assert item["comment"].startswith("=")
    assert item["submitted_at"]
    assert summary.status_code == 200
    assert summary.json()["total_submissions"] == 1
    assert summary.json()["average_rating"] == 4.0
    assert summary.json()["environmental"]["very_important"] == 1
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(StringIO(export.content.decode("utf-8-sig"))))
    assert len(rows) == 1
    assert rows[0]["comment"].startswith("'=HYPERLINK(")
    assert export.headers["cache-control"] == "no-store"

    legacy_export = client.get("/api/analytics/export", headers=headers)
    assert legacy_export.status_code == 200


def test_admin_auth_configuration_failure_is_explicit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("U_INVEST_ADMIN_USER_IDS", ADMIN_ID)
    monkeypatch.setattr(
        dependencies,
        "verify_supabase_access_token",
        lambda _token, _issuer: {"sub": ADMIN_ID},
    )

    response = client.get(
        "/api/admin/feedback",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 503


def test_admin_cors_preflight_allows_authorization_header(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/admin/feedback",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_swagger_and_openapi_include_all_routes(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    schema_response = client.get("/openapi.json")

    assert schema_response.status_code == 200
    paths = schema_response.json()["paths"]
    assert {
        "/api/health",
        "/api/experiments/assign",
        "/api/analytics/events",
        "/api/feedback",
        "/api/analytics/summary",
        "/api/analytics/sustainability",
        "/api/analytics/export",
        "/api/admin/feedback",
        "/api/admin/feedback/summary",
        "/api/admin/feedback/export",
    }.issubset(paths)
    admin_operation = paths["/api/admin/feedback"]["get"]
    assert admin_operation["security"] == [{"HTTPBearer": []}]
    assert "401" in admin_operation["responses"]
    feedback_operation = paths["/api/feedback"]["post"]
    assert "422" in feedback_operation["responses"]
    request_schema = feedback_operation["requestBody"]["content"][
        "application/json"
    ]["schema"]
    schema_name = request_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    feedback_example = schema_response.json()["components"]["schemas"][
        schema_name
    ]["examples"][0]
    assert feedback_example["investment_interest"] == "maybe"
