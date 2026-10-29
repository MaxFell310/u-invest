from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"visitor_id": "123e4567-e89b-42d3-a456-426614174000"}]
        }
    )

    visitor_id: UUID


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_name: str
    variant: Literal["A", "B"]
    assigned_at: datetime
