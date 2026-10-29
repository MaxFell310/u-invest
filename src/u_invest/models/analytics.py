from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UTCDateTime


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["visitor_id", "experiment_name", "variant"],
            [
                "experiment_assignments.visitor_id",
                "experiment_assignments.experiment_name",
                "experiment_assignments.variant",
            ],
            name="fk_event_experiment_assignment",
        ),
        UniqueConstraint("event_id", name="uq_analytics_event_event_id"),
        CheckConstraint(
            "event_name IN ('page_view', 'cta_click')",
            name="ck_analytics_event_name",
        ),
        Index("ix_event_experiment_variant_name", "experiment_name", "variant", "event_name"),
        Index("ix_event_visitor_experiment", "visitor_id", "experiment_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    experiment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variant: Mapped[str] = mapped_column(String(1), nullable=False)
    event_name: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )
