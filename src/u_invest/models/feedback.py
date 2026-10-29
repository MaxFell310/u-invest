from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UTCDateTime


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5",
            name="ck_feedback_rating",
        ),
        CheckConstraint(
            "investment_interest IN ('yes', 'maybe', 'no')",
            name="ck_feedback_investment_interest",
        ),
        CheckConstraint(
            "environmental_importance IN "
            "('not_important', 'slightly_important', 'moderately_important', "
            "'very_important', 'unsure')",
            name="ck_feedback_environmental_importance",
        ),
        CheckConstraint(
            "social_importance IN "
            "('not_important', 'slightly_important', 'moderately_important', "
            "'very_important', 'unsure')",
            name="ck_feedback_social_importance",
        ),
        CheckConstraint(
            "ethical_importance IN "
            "('not_important', 'slightly_important', 'moderately_important', "
            "'very_important', 'unsure')",
            name="ck_feedback_ethical_importance",
        ),
        CheckConstraint(
            "comment IS NULL OR length(comment) <= 1000",
            name="ck_feedback_comment_length",
        ),
        Index("ix_feedback_submitted_at", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investment_interest: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    environmental_importance: Mapped[str] = mapped_column(String(24), nullable=False)
    social_importance: Mapped[str] = mapped_column(String(24), nullable=False)
    ethical_importance: Mapped[str] = mapped_column(String(24), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), nullable=False
    )
