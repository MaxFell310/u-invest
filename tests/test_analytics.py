from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import approx

from u_invest.constants import EXPERIMENT_NAME
from u_invest.database import create_database_engine
from u_invest.main import create_app


def assign(client: TestClient, visitor_id: str) -> dict[str, str]:
    response = client.post(
        "/api/experiments/assign",
        json={"visitor_id": visitor_id},
    )
    assert response.status_code == 200
    return response.json()


def record_click(
    client: TestClient, visitor_id: str, variant: str, event_id: str | None = None
):
    return client.post(
        "/api/analytics/events",
        json={
            "event_id": event_id or str(uuid4()),
            "visitor_id": visitor_id,
            "experiment_name": EXPERIMENT_NAME,
            "variant": variant,
            "event_name": "cta_click",
        },
    )


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_missing_database_schema() -> None:
    engine = create_database_engine("sqlite://")
    app = create_app(engine)
    try:
        with TestClient(app) as client:
            response = client.get("/api/health")
    finally:
        engine.dispose()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database schema is not initialized. Run `uv run alembic upgrade head`."
    }


def test_assignment_is_persisted_and_consistent(client: TestClient) -> None:
    visitor_id = str(uuid4())

    first = assign(client, visitor_id)
    second = assign(client, visitor_id)

    assert first["variant"] in {"A", "B"}
    assert second["variant"] == first["variant"]
    assert first["experiment_name"] == EXPERIMENT_NAME
    assert datetime.fromisoformat(first["assigned_at"]).utcoffset() == timedelta(0)


def test_event_name_validation_rejects_unknown_events(client: TestClient) -> None:
    visitor_id = str(uuid4())
    assignment = assign(client, visitor_id)
    response = client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "visitor_id": visitor_id,
            "experiment_name": EXPERIMENT_NAME,
            "variant": assignment["variant"],
            "event_name": "unknown_event",
        },
    )

    assert response.status_code == 422


def test_event_requires_matching_assignment_variant(client: TestClient) -> None:
    visitor_id = str(uuid4())
    assignment = assign(client, visitor_id)
    wrong_variant = "B" if assignment["variant"] == "A" else "A"
    response = record_click(client, visitor_id, wrong_variant)

    assert response.status_code == 409


def test_summary_uses_unique_conversions_and_total_clicks(client: TestClient) -> None:
    visitors = [str(uuid4()) for _ in range(3)]
    assignments = [assign(client, visitor_id) for visitor_id in visitors]
    click_variant = assignments[0]["variant"]

    assert record_click(client, visitors[0], click_variant).status_code == 201
    assert record_click(client, visitors[0], click_variant).status_code == 201

    response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    assert response.json()["participants"] == 3
    result_by_variant = {
        item["variant"]: item for item in response.json()["variants"]
    }
    clicked = result_by_variant[click_variant]
    expected_visitors = sum(
        assignment["variant"] == click_variant for assignment in assignments
    )
    assert clicked["visitors_assigned"] == expected_visitors
    assert clicked["unique_cta_conversions"] == 1
    assert clicked["total_cta_clicks"] == 2
    assert clicked["conversion_rate_percent"] == approx(
        100 / clicked["visitors_assigned"]
    )


def test_event_id_retry_does_not_duplicate_event(client: TestClient) -> None:
    visitor_id = str(uuid4())
    assignment = assign(client, visitor_id)
    event_id = str(uuid4())

    first = record_click(client, visitor_id, assignment["variant"], event_id)
    retry = record_click(client, visitor_id, assignment["variant"], event_id)

    assert first.status_code == 201
    assert retry.status_code == 200
    metrics = client.get("/api/analytics/summary").json()["variants"]
    clicked_variant = next(
        metric for metric in metrics if metric["variant"] == assignment["variant"]
    )
    assert clicked_variant["total_cta_clicks"] == 1
    assert clicked_variant["unique_cta_conversions"] == 1


def test_page_views_are_counted_separately_from_cta_clicks(
    client: TestClient,
) -> None:
    visitor_id = str(uuid4())
    assignment = assign(client, visitor_id)
    response = client.post(
        "/api/analytics/events",
        json={
            "event_id": str(uuid4()),
            "visitor_id": visitor_id,
            "experiment_name": EXPERIMENT_NAME,
            "variant": assignment["variant"],
            "event_name": "page_view",
        },
    )

    assert response.status_code == 201
    metrics = client.get("/api/analytics/summary").json()["variants"]
    variant = next(
        item for item in metrics if item["variant"] == assignment["variant"]
    )
    assert variant["total_page_views"] == 1
    assert variant["total_cta_clicks"] == 0
    assert variant["unique_cta_conversions"] == 0


def test_summary_includes_actual_assignment_period(client: TestClient) -> None:
    visitor_id = str(uuid4())
    assign(client, visitor_id)

    summary = client.get("/api/analytics/summary").json()

    assert summary["participants"] == 1
    assert summary["testing_started_at"] is not None
    assert summary["last_activity_at"] is not None
    assert summary["testing_started_at"] <= summary["last_activity_at"]


def test_empty_summary_has_zero_counts_and_rates(client: TestClient) -> None:
    response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    assert response.json()["participants"] == 0
    assert response.json()["testing_started_at"] is None
    assert response.json()["last_activity_at"] is None
    assert response.json()["feedback_submissions"] == 0
    assert response.json()["average_rating"] is None
    assert response.json()["investment_interest"] == {
        "yes": 0,
        "maybe": 0,
        "no": 0,
    }
    for variant in response.json()["variants"]:
        assert variant["visitors_assigned"] == 0
        assert variant["total_page_views"] == 0
        assert variant["unique_cta_conversions"] == 0
        assert variant["total_cta_clicks"] == 0
        assert variant["conversion_rate_percent"] == 0
