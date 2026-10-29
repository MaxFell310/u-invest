from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


def valid_feedback(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rating": 5,
        "investment_interest": "yes",
        "comment": "Interested in learning more.",
        "environmental_importance": "very_important",
        "social_importance": "moderately_important",
        "ethical_importance": "very_important",
    }
    payload.update(overrides)
    return payload


def test_feedback_submission_and_summary(client: TestClient) -> None:
    response = client.post(
        "/api/feedback",
        json=valid_feedback(rating=None, comment="   "),
    )

    assert response.status_code == 201
    assert response.json()["submission_id"] > 0
    submitted_at = datetime.fromisoformat(
        response.json()["submitted_at"].replace("Z", "+00:00")
    )
    assert submitted_at.utcoffset() == timedelta(0)

    summary = client.get("/api/analytics/summary").json()
    assert summary["feedback_submissions"] == 1
    assert summary["average_rating"] is None
    assert summary["investment_interest"] == {
        "yes": 1,
        "maybe": 0,
        "no": 0,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"rating": 0},
        {"rating": 6},
        {"rating": True},
        {"investment_interest": "certainly"},
        {"environmental_importance": "unsure-ish"},
        {"social_importance": None},
        {"ethical_importance": "very_important", "comment": "x" * 1001},
    ],
)
def test_invalid_feedback_is_rejected(
    client: TestClient, overrides: dict[str, object]
) -> None:
    response = client.post("/api/feedback", json=valid_feedback(**overrides))

    assert response.status_code == 422
    assert client.get("/api/analytics/summary").json()["feedback_submissions"] == 0


def test_sustainability_aggregates_real_responses(client: TestClient) -> None:
    first = valid_feedback(
        rating=5,
        investment_interest="yes",
        environmental_importance="very_important",
        social_importance="moderately_important",
        ethical_importance="very_important",
    )
    second = valid_feedback(
        rating=3,
        investment_interest="no",
        environmental_importance="not_important",
        social_importance="very_important",
        ethical_importance="unsure",
    )

    assert client.post("/api/feedback", json=first).status_code == 201
    assert client.post("/api/feedback", json=second).status_code == 201

    sustainability = client.get("/api/analytics/sustainability")
    assert sustainability.status_code == 200
    assert sustainability.json() == {
        "response_count": 2,
        "environmental": {
            "not_important": 1,
            "slightly_important": 0,
            "moderately_important": 0,
            "very_important": 1,
            "unsure": 0,
        },
        "social": {
            "not_important": 0,
            "slightly_important": 0,
            "moderately_important": 1,
            "very_important": 1,
            "unsure": 0,
        },
        "ethical": {
            "not_important": 0,
            "slightly_important": 0,
            "moderately_important": 0,
            "very_important": 1,
            "unsure": 1,
        },
    }

    summary = client.get("/api/analytics/summary").json()
    assert summary["feedback_submissions"] == 2
    assert summary["average_rating"] == 4.0
    assert summary["investment_interest"] == {
        "yes": 1,
        "maybe": 0,
        "no": 1,
    }


def test_sustainability_and_cors_when_no_responses(client: TestClient) -> None:
    sustainability = client.get("/api/analytics/sustainability")
    assert sustainability.status_code == 200
    assert sustainability.json()["response_count"] == 0
    assert set(sustainability.json()["environmental"].values()) == {0}

    preflight = client.options(
        "/api/feedback",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5500"
