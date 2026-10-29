from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import (
    EXPERIMENT_NAME,
    IMPORTANCE_OPTIONS,
    INVESTMENT_INTEREST_OPTIONS,
)
from ..models.analytics import AnalyticsEvent
from ..models.experiments import ExperimentAssignment
from ..models.feedback import Feedback
from ..schemas.analytics import (
    AnalyticsSummary,
    SustainabilitySummary,
    VariantAnalytics,
)
from ..schemas.feedback import Importance, InvestmentInterest


def build_analytics_summary(session: Session) -> AnalyticsSummary:
    assigned_counts = dict(
        session.execute(
            select(ExperimentAssignment.variant, func.count())
            .where(ExperimentAssignment.experiment_name == EXPERIMENT_NAME)
            .group_by(ExperimentAssignment.variant)
        ).all()
    )
    click_counts = {
        variant: (total_clicks, unique_conversions)
        for variant, total_clicks, unique_conversions in session.execute(
            select(
                AnalyticsEvent.variant,
                func.count(AnalyticsEvent.id),
                func.count(func.distinct(AnalyticsEvent.visitor_id)),
            )
            .where(
                AnalyticsEvent.experiment_name == EXPERIMENT_NAME,
                AnalyticsEvent.event_name == "cta_click",
            )
            .group_by(AnalyticsEvent.variant)
        ).all()
    }
    page_view_counts = dict(
        session.execute(
            select(AnalyticsEvent.variant, func.count(AnalyticsEvent.id))
            .where(
                AnalyticsEvent.experiment_name == EXPERIMENT_NAME,
                AnalyticsEvent.event_name == "page_view",
            )
            .group_by(AnalyticsEvent.variant)
        ).all()
    )

    variants: list[VariantAnalytics] = []
    for variant in ("A", "B"):
        visitors_assigned = assigned_counts.get(variant, 0)
        total_clicks, unique_conversions = click_counts.get(variant, (0, 0))
        conversion_rate = (
            unique_conversions / visitors_assigned * 100
            if visitors_assigned
            else 0.0
        )
        variants.append(
            VariantAnalytics(
                variant=variant,
                visitors_assigned=visitors_assigned,
                total_page_views=page_view_counts.get(variant, 0),
                unique_cta_conversions=unique_conversions,
                total_cta_clicks=total_clicks,
                conversion_rate_percent=conversion_rate,
            )
        )

    feedback_submissions, average_rating = session.execute(
        select(func.count(Feedback.id), func.avg(Feedback.rating))
    ).one()
    interest_counts = {
        response: 0 for response in INVESTMENT_INTEREST_OPTIONS
    }
    interest_counts.update(
        dict(
            session.execute(
                select(Feedback.investment_interest, func.count())
                .group_by(Feedback.investment_interest)
            ).all()
        )
    )

    first_assignment_at = session.scalar(
        select(func.min(ExperimentAssignment.assigned_at)).where(
            ExperimentAssignment.experiment_name == EXPERIMENT_NAME
        )
    )
    first_feedback_at = session.scalar(select(func.min(Feedback.submitted_at)))
    last_assignment_at = session.scalar(
        select(func.max(ExperimentAssignment.assigned_at)).where(
            ExperimentAssignment.experiment_name == EXPERIMENT_NAME
        )
    )
    last_event_at = session.scalar(
        select(func.max(AnalyticsEvent.occurred_at)).where(
            AnalyticsEvent.experiment_name == EXPERIMENT_NAME
        )
    )
    last_feedback_at = session.scalar(select(func.max(Feedback.submitted_at)))
    start_dates = [
        value
        for value in (first_assignment_at, first_feedback_at)
        if value is not None
    ]
    activity_dates = [
        value
        for value in (last_assignment_at, last_event_at, last_feedback_at)
        if value is not None
    ]

    return AnalyticsSummary(
        experiment_name=EXPERIMENT_NAME,
        participants=sum(assigned_counts.values()),
        testing_started_at=min(start_dates) if start_dates else None,
        last_activity_at=max(activity_dates) if activity_dates else None,
        variants=variants,
        feedback_submissions=feedback_submissions,
        average_rating=(
            float(average_rating) if average_rating is not None else None
        ),
        investment_interest=interest_counts,
    )


def build_sustainability_summary(session: Session) -> SustainabilitySummary:
    distributions: dict[str, dict[str, int]] = {}
    for field in (
        "environmental_importance",
        "social_importance",
        "ethical_importance",
    ):
        column = getattr(Feedback, field)
        counts = {response: 0 for response in IMPORTANCE_OPTIONS}
        counts.update(
            dict(
                session.execute(
                    select(column, func.count()).group_by(column)
                ).all()
            )
        )
        distributions[field] = counts

    return SustainabilitySummary(
        response_count=session.scalar(select(func.count(Feedback.id))) or 0,
        environmental=distributions["environmental_importance"],
        social=distributions["social_importance"],
        ethical=distributions["ethical_importance"],
    )
