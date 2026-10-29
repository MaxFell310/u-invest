from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from ..dependencies import get_db, require_admin
from ..models.feedback import Feedback
from ..schemas.feedback import (
    AdminFeedbackItem,
    AdminFeedbackPage,
    AdminFeedbackSummary,
    Importance,
    InvestmentInterest,
)
from ..services.export_service import build_feedback_export

router = APIRouter(tags=["administrator"])


@router.get(
    "/feedback",
    response_model=AdminFeedbackPage,
    summary="List feedback submissions",
    description="Returns a paginated, newest-first list. Optional filters can narrow the response by comment text, rating, interest, or sustainability answer.",
    responses={
        401: {"description": "Missing, invalid, or expired access token."},
        403: {"description": "Authenticated user is not an authorized collaborator."},
        503: {"description": "Authentication provider is unavailable or not configured."},
    },
)
def list_feedback(
    _admin_subject: str = Depends(require_admin),
    session: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="One-based result page."),
    page_size: int = Query(
        default=25, ge=1, le=100, description="Maximum number of records to return."
    ),
    q: str | None = Query(
        default=None, max_length=100, description="Substring to find in comments."
    ),
    rating: int | None = Query(
        default=None, ge=1, le=5, description="Filter by the submitted rating."
    ),
    investment_interest: InvestmentInterest | None = Query(
        default=None, description="Filter by investment-interest response."
    ),
    environmental_importance: Importance | None = Query(
        default=None, description="Filter by environmental importance response."
    ),
    social_importance: Importance | None = Query(
        default=None, description="Filter by social importance response."
    ),
    ethical_importance: Importance | None = Query(
        default=None, description="Filter by ethical importance response."
    ),
) -> AdminFeedbackPage:
    filters = _feedback_filters(
        q=q,
        rating=rating,
        investment_interest=investment_interest,
        environmental_importance=environmental_importance,
        social_importance=social_importance,
        ethical_importance=ethical_importance,
    )
    total = session.scalar(
        select(func.count(Feedback.id)).where(*filters)
    ) or 0
    records = session.scalars(
        select(Feedback)
        .where(*filters)
        .order_by(Feedback.submitted_at.desc(), Feedback.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminFeedbackPage(
        items=[AdminFeedbackItem.model_validate(record) for record in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/feedback/summary",
    response_model=AdminFeedbackSummary,
    summary="Get feedback dashboard statistics",
    description="Returns counts and averages over all stored survey submissions.",
    responses={
        401: {"description": "Missing, invalid, or expired access token."},
        403: {"description": "Authenticated user is not an authorized collaborator."},
    },
)
def feedback_summary(
    _admin_subject: str = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AdminFeedbackSummary:
    total, average_rating = session.execute(
        select(func.count(Feedback.id), func.avg(Feedback.rating))
    ).one()
    interest = _distribution(session, Feedback.investment_interest)
    environmental = _distribution(session, Feedback.environmental_importance)
    social = _distribution(session, Feedback.social_importance)
    ethical = _distribution(session, Feedback.ethical_importance)
    return AdminFeedbackSummary(
        total_submissions=total,
        average_rating=(
            float(average_rating) if average_rating is not None else None
        ),
        investment_interest=interest,
        environmental=environmental,
        social=social,
        ethical=ethical,
    )


@router.get(
    "/feedback/export",
    response_class=Response,
    summary="Export feedback submissions as CSV",
    description="Downloads raw feedback, including comments. Requires an allowlisted Supabase collaborator account.",
    responses={
        401: {"description": "Missing, invalid, or expired access token."},
        403: {"description": "Authenticated user is not an authorized collaborator."},
    },
)
def export_feedback(
    _admin_subject: str = Depends(require_admin),
    session: Session = Depends(get_db),
) -> Response:
    return Response(
        content=build_feedback_export(session),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="u-invest-feedback.csv"',
            "Cache-Control": "no-store",
        },
    )


def _feedback_filters(
    *,
    q: str | None,
    rating: int | None,
    investment_interest: str | None,
    environmental_importance: str | None,
    social_importance: str | None,
    ethical_importance: str | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if q and q.strip():
        filters.append(Feedback.comment.ilike(f"%{q.strip()}%"))
    if rating is not None:
        filters.append(Feedback.rating == rating)
    if investment_interest is not None:
        filters.append(Feedback.investment_interest == investment_interest)
    if environmental_importance is not None:
        filters.append(Feedback.environmental_importance == environmental_importance)
    if social_importance is not None:
        filters.append(Feedback.social_importance == social_importance)
    if ethical_importance is not None:
        filters.append(Feedback.ethical_importance == ethical_importance)
    return filters


def _distribution(
    session: Session, column: InstrumentedAttribute[str]
) -> dict[str, int]:
    rows = session.execute(
        select(column, func.count()).group_by(column)
    ).all()
    return {str(value): count for value, count in rows}
