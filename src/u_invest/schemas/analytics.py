from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..constants import EXPERIMENT_NAME
from .feedback import Importance, InvestmentInterest


class AnalyticsEventCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_id": "223e4567-e89b-42d3-a456-426614174000",
                    "visitor_id": "123e4567-e89b-42d3-a456-426614174000",
                    "experiment_name": EXPERIMENT_NAME,
                    "variant": "A",
                    "event_name": "cta_click",
                }
            ]
        }
    )

    event_id: UUID
    visitor_id: UUID
    experiment_name: str = Field(
        default=EXPERIMENT_NAME, min_length=1, max_length=100
    )
    variant: Literal["A", "B"]
    event_name: Literal["page_view", "cta_click"]


class AnalyticsEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    experiment_name: str
    variant: Literal["A", "B"]
    event_name: Literal["page_view", "cta_click"]
    occurred_at: datetime


class VariantAnalytics(BaseModel):
    variant: Literal["A", "B"]
    visitors_assigned: int
    total_page_views: int
    unique_cta_conversions: int
    total_cta_clicks: int
    conversion_rate_percent: float


class AnalyticsSummary(BaseModel):
    experiment_name: str
    participants: int
    testing_started_at: datetime | None
    last_activity_at: datetime | None
    variants: list[VariantAnalytics]
    feedback_submissions: int
    average_rating: float | None
    investment_interest: dict[InvestmentInterest, int]


class SustainabilitySummary(BaseModel):
    response_count: int
    environmental: dict[Importance, int]
    social: dict[Importance, int]
    ethical: dict[Importance, int]
