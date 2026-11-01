"""Add user profiles and demo portfolio tables.

Revision ID: 8a32f6d1c907
Revises: 5cd88cefc1e9
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a32f6d1c907"
down_revision: Union[str, Sequence[str], None] = "5cd88cefc1e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "demo_wallets",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "balance >= 0", name="ck_demo_wallet_nonnegative_balance"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "portfolio_positions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(length=12), nullable=False),
        sa.Column("company", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("average_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("invested_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name="ck_position_positive_quantity"
        ),
        sa.CheckConstraint(
            "average_price > 0", name="ck_position_positive_average_price"
        ),
        sa.CheckConstraint(
            "invested_amount > 0", name="ck_position_positive_invested_amount"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "ticker", name="uq_position_user_ticker"),
    )
    op.create_index(
        "ix_position_user_ticker",
        "portfolio_positions",
        ["user_id", "ticker"],
        unique=False,
    )
    op.create_table(
        "portfolio_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_type", sa.String(length=16), nullable=False),
        sa.Column("ticker", sa.String(length=12), nullable=True),
        sa.Column("company", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transaction_type IN ('deposit', 'buy', 'sell')",
            name="ck_transaction_type",
        ),
        sa.CheckConstraint("amount > 0", name="ck_transaction_positive_amount"),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_transaction_positive_quantity",
        ),
        sa.CheckConstraint(
            "unit_price IS NULL OR unit_price > 0",
            name="ck_transaction_positive_unit_price",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "request_id", name="uq_transaction_user_request"
        ),
    )
    op.create_index(
        "ix_transaction_user_created",
        "portfolio_transactions",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_user_created", table_name="portfolio_transactions")
    op.drop_table("portfolio_transactions")
    op.drop_index("ix_position_user_ticker", table_name="portfolio_positions")
    op.drop_table("portfolio_positions")
    op.drop_table("demo_wallets")
    op.drop_table("user_profiles")
