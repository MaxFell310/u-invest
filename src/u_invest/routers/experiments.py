import secrets

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..constants import EXPERIMENT_NAME
from ..dependencies import get_db
from ..models.experiments import ExperimentAssignment
from ..schemas.experiments import AssignmentRequest, AssignmentResponse

router = APIRouter(tags=["experiments"])


@router.post(
    "/assign",
    response_model=AssignmentResponse,
    summary="Assign a visitor to an experiment variant",
    description="Returns the stable stored assignment for this anonymous visitor, creating a random A/B assignment on first use.",
    responses={422: {"description": "Visitor identifier is invalid."}},
)
def assign_visitor(
    payload: AssignmentRequest,
    session: Session = Depends(get_db),
) -> ExperimentAssignment:
    visitor_id = str(payload.visitor_id)
    assignment = session.scalar(
        select(ExperimentAssignment).where(
            ExperimentAssignment.visitor_id == visitor_id,
            ExperimentAssignment.experiment_name == EXPERIMENT_NAME,
        )
    )
    if assignment is not None:
        return assignment

    assignment = ExperimentAssignment(
        visitor_id=visitor_id,
        experiment_name=EXPERIMENT_NAME,
        variant=secrets.choice(("A", "B")),
    )
    session.add(assignment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        assignment = session.scalar(
            select(ExperimentAssignment).where(
                ExperimentAssignment.visitor_id == visitor_id,
                ExperimentAssignment.experiment_name == EXPERIMENT_NAME,
            )
        )
        if assignment is None:
            raise
    else:
        session.refresh(assignment)
    return assignment
