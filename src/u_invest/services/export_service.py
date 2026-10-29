import csv
from datetime import datetime
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.analytics import AnalyticsEvent
from ..models.experiments import ExperimentAssignment
from ..models.feedback import Feedback

CSV_COLUMNS = (
    "record_type",
    "record_id",
    "visitor_id",
    "experiment_name",
    "variant",
    "event_id",
    "event_name",
    "occurred_at",
    "rating",
    "investment_interest",
    "comment",
    "environmental_importance",
    "social_importance",
    "ethical_importance",
    "submitted_at",
)
FEEDBACK_CSV_COLUMNS = (
    "submission_id",
    "submitted_at",
    "rating",
    "investment_interest",
    "comment",
    "environmental_importance",
    "social_importance",
    "ethical_importance",
)


def build_analytics_export(session: Session) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)

    assignments = session.scalars(
        select(ExperimentAssignment).order_by(ExperimentAssignment.assigned_at)
    )
    for assignment in assignments:
        writer.writerow(
            _safe_row(
                "assignment",
                assignment.id,
                assignment.visitor_id,
                assignment.experiment_name,
                assignment.variant,
                occurred_at=assignment.assigned_at,
            )
        )

    events = session.scalars(
        select(AnalyticsEvent).order_by(AnalyticsEvent.occurred_at)
    )
    for event in events:
        writer.writerow(
            _safe_row(
                "event",
                event.id,
                event.visitor_id,
                event.experiment_name,
                event.variant,
                event.event_id,
                event.event_name,
                event.occurred_at,
            )
        )

    feedback_records = session.scalars(
        select(Feedback).order_by(Feedback.submitted_at)
    )
    for feedback in feedback_records:
        writer.writerow(
            _safe_row(
                "feedback",
                feedback.id,
                rating=feedback.rating,
                investment_interest=feedback.investment_interest,
                comment=feedback.comment,
                environmental_importance=feedback.environmental_importance,
                social_importance=feedback.social_importance,
                ethical_importance=feedback.ethical_importance,
                submitted_at=feedback.submitted_at,
            )
        )

    return "\ufeff" + output.getvalue()


def build_feedback_export(session: Session) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(FEEDBACK_CSV_COLUMNS)
    feedback_records = session.scalars(
        select(Feedback).order_by(Feedback.submitted_at, Feedback.id)
    )
    for feedback in feedback_records:
        writer.writerow(
            tuple(
                _spreadsheet_safe(value)
                for value in (
                    feedback.id,
                    feedback.submitted_at.isoformat(),
                    feedback.rating if feedback.rating is not None else "",
                    feedback.investment_interest,
                    feedback.comment or "",
                    feedback.environmental_importance,
                    feedback.social_importance,
                    feedback.ethical_importance,
                )
            )
        )
    return "\ufeff" + output.getvalue()


def _safe_row(
    record_type: str,
    record_id: int,
    visitor_id: str = "",
    experiment_name: str = "",
    variant: str = "",
    event_id: str = "",
    event_name: str = "",
    occurred_at: datetime | None = None,
    rating: int | None = None,
    investment_interest: str = "",
    comment: str | None = None,
    environmental_importance: str = "",
    social_importance: str = "",
    ethical_importance: str = "",
    submitted_at: datetime | None = None,
) -> tuple[str | int, ...]:
    values = (
        record_type,
        record_id,
        visitor_id,
        experiment_name,
        variant,
        event_id,
        event_name,
        occurred_at.isoformat() if occurred_at else "",
        rating if rating is not None else "",
        investment_interest,
        comment or "",
        environmental_importance,
        social_importance,
        ethical_importance,
        submitted_at.isoformat() if submitted_at else "",
    )
    return tuple(_spreadsheet_safe(value) for value in values)


def _spreadsheet_safe(value: str | int) -> str | int:
    if isinstance(value, str) and (
        value.startswith(("\t", "\r"))
        or value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
    ):
        return f"'{value}"
    return value
