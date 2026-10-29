from pathlib import Path

from fastapi.testclient import TestClient

from u_invest.database import create_database_engine
from u_invest.main import create_app
from u_invest.models import Base


def test_feedback_survives_application_restart(tmp_path: Path) -> None:
    database_path = (tmp_path / "persistent.sqlite").as_posix()
    database_url = f"sqlite:///{database_path}"
    first_engine = create_database_engine(database_url)
    Base.metadata.create_all(first_engine)
    first_app = create_app(first_engine)

    with TestClient(first_app) as first_client:
        submission = first_client.post(
            "/api/feedback",
            json={
                "rating": 5,
                "investment_interest": "yes",
                "comment": "Persist this response.",
                "environmental_importance": "very_important",
                "social_importance": "very_important",
                "ethical_importance": "very_important",
            },
        )
    first_engine.dispose()
    assert submission.status_code == 201

    restarted_engine = create_database_engine(database_url)
    restarted_app = create_app(restarted_engine)
    with TestClient(restarted_app) as restarted_client:
        summary = restarted_client.get("/api/analytics/summary")

    restarted_engine.dispose()
    assert summary.status_code == 200
    assert summary.json()["feedback_submissions"] == 1
    assert summary.json()["average_rating"] == 5.0
