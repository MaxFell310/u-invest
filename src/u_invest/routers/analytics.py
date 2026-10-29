from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..constants import EXPERIMENT_NAME
from ..dependencies import get_db, require_admin
from ..models.analytics import AnalyticsEvent
from ..models.experiments import ExperimentAssignment
from ..schemas.analytics import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    AnalyticsSummary,
    SustainabilitySummary,
)
from ..schemas.feedback import Importance, InvestmentInterest
from ..services.analytics_service import (
    build_analytics_summary,
    build_sustainability_summary,
)
from ..services.export_service import build_analytics_export

router = APIRouter(tags=["analytics"])


@router.post(
    "/events",
    response_model=AnalyticsEventResponse,
    status_code=201,
    summary="Record an experiment event",
    description="Record an allowed page view or CTA click for the visitor's assigned variant. Reusing an identical event ID is idempotent.",
    responses={
        200: {
            "model": AnalyticsEventResponse,
            "description": "The matching event was already recorded; no duplicate was created.",
        },
        404: {"description": "Experiment assignment does not exist."},
        409: {"description": "Variant mismatch or event ID conflict."},
        422: {"description": "Request validation failed."},
    },
)
def record_event(
    payload: AnalyticsEventCreate,
    response: Response,
    session: Session = Depends(get_db),
) -> AnalyticsEvent:
    event_id = str(payload.event_id)
    visitor_id = str(payload.visitor_id)
    existing_event = session.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
    )
    if existing_event is not None:
        if not _matches_event(existing_event, payload):
            raise HTTPException(
                status_code=409,
                detail="The event ID has already been used for different event data.",
            )
        response.status_code = 200
        return existing_event

    assignment = session.scalar(
        select(ExperimentAssignment).where(
            ExperimentAssignment.visitor_id == visitor_id,
            ExperimentAssignment.experiment_name == payload.experiment_name,
        )
    )
    if assignment is None:
        raise HTTPException(
            status_code=404, detail="No assignment exists for this visitor."
        )
    if assignment.variant != payload.variant:
        raise HTTPException(
            status_code=409,
            detail="The submitted variant does not match the visitor assignment.",
        )
    if payload.experiment_name != EXPERIMENT_NAME:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    event = AnalyticsEvent(
        event_id=event_id,
        visitor_id=visitor_id,
        experiment_name=payload.experiment_name,
        variant=assignment.variant,
        event_name=payload.event_name,
    )
    session.add(event)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        existing_event = session.scalar(
            select(AnalyticsEvent).where(AnalyticsEvent.event_id == event_id)
        )
        if existing_event is not None and _matches_event(existing_event, payload):
            response.status_code = 200
            return existing_event
        raise HTTPException(
            status_code=409, detail="The event could not be recorded."
        ) from error
    session.refresh(event)
    return event


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Get aggregate experiment metrics",
    description="Returns aggregate counts and conversion rates. No visitor-level records are exposed.",
)
def get_analytics_summary(
    session: Session = Depends(get_db),
) -> AnalyticsSummary:
    return build_analytics_summary(session)


@router.get(
    "/sustainability",
    response_model=SustainabilitySummary,
    summary="Get aggregate sustainability responses",
    description="Returns distributions calculated from submitted feedback only.",
)
def get_sustainability_summary(
    session: Session = Depends(get_db),
) -> SustainabilitySummary:
    return build_sustainability_summary(session)


@router.get(
    "/export",
    response_class=Response,
    dependencies=[Depends(require_admin)],
    summary="Export collected experiment and feedback data",
    description="Downloads raw analytics and feedback records. Requires an allowlisted Supabase collaborator account.",
    responses={
        401: {"description": "Missing, invalid, or expired access token."},
        403: {"description": "Authenticated user is not an authorized collaborator."},
        503: {"description": "Authentication provider is unavailable or not configured."},
    },
)
def export_analytics(session: Session = Depends(get_db)) -> Response:
    return Response(
        content=build_analytics_export(session),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="u-invest-analytics.csv"',
            "Cache-Control": "no-store",
        },
    )


def _matches_event(
    event: AnalyticsEvent, payload: AnalyticsEventCreate
) -> bool:
    return (
        event.visitor_id == str(payload.visitor_id)
        and event.experiment_name == payload.experiment_name
        and event.variant == payload.variant
        and event.event_name == payload.event_name
    )
