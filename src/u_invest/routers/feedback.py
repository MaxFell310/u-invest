from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models.feedback import Feedback
from ..schemas.feedback import FeedbackCreate, FeedbackSubmissionResponse

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackSubmissionResponse,
    status_code=201,
    summary="Submit anonymous feedback",
    description="Validates and stores a survey response without collecting a visitor identifier or other personal information.",
    responses={422: {"description": "A response is invalid or exceeds its allowed length."}},
)
def submit_feedback(
    payload: FeedbackCreate,
    session: Session = Depends(get_db),
) -> FeedbackSubmissionResponse:
    feedback = Feedback(**payload.model_dump())
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return FeedbackSubmissionResponse(
        submission_id=feedback.id,
        submitted_at=feedback.submitted_at,
    )
