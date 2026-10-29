from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UTCDateTime


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint(
            "visitor_id",
            "experiment_name",
            name="uq_assignment_visitor_experiment",
        ),
        UniqueConstraint(
            "visitor_id",
            "experiment_name",
            "variant",
            name="uq_assignment_visitor_experiment_variant",
        ),
        CheckConstraint("variant IN ('A', 'B')", name="ck_assignment_variant"),
        Index("ix_assignment_experiment_variant", "experiment_name", "variant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    experiment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variant: Mapped[str] = mapped_column(String(1), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )
