import csv
from io import StringIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from u_invest import dependencies
from u_invest.constants import EXPERIMENT_NAME

ADMIN_ID = str(uuid4())


def test_analytics_export_is_available_only_to_admin_collaborators(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://u-invest-test.supabase.co")
    monkeypatch.setenv("U_INVEST_ADMIN_USER_IDS", ADMIN_ID)
    monkeypatch.setattr(
        dependencies,
        "verify_supabase_access_token",
        lambda _token, _issuer: {"sub": ADMIN_ID},
    )
    visitor_id = str(uuid4())
    assignment = client.post(
        "/api/experiments/assign",
        json={"visitor_id": visitor_id},
    ).json()
    event = client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "visitor_id": visitor_id,
            "experiment_name": EXPERIMENT_NAME,
            "variant": assignment["variant"],
            "event_name": "cta_click",
        },
    )
    feedback = client.post(
        "/api/feedback",
        json={
            "rating": 4,
            "investment_interest": "maybe",
            "comment": "=SUM(1,2)",
            "environmental_importance": "moderately_important",
            "social_importance": "very_important",
            "ethical_importance": "unsure",
        },
    )

    assert event.status_code == 201
    assert feedback.status_code == 201
    assert client.get("/api/analytics/export").status_code == 401
    response = client.get(
        "/api/analytics/export",
        headers={"Authorization": "Bearer admin-test-token"},
    )

    assert response.status_code == 200
    rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
    assert [row["record_type"] for row in rows] == [
        "assignment",
        "event",
        "feedback",
    ]
    assert rows[0]["visitor_id"] == visitor_id
    assert rows[1]["event_name"] == "cta_click"
    assert rows[2]["comment"].startswith("'=SUM(")
