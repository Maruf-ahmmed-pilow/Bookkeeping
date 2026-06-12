import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Portable column types: native ``uuid``/``jsonb`` on PostgreSQL (production),
# transparently degrading to ``varchar``/``json`` on other backends such as the
# in-memory SQLite database used by the test suite.
GUID = String(36).with_variant(PgUUID(as_uuid=False), "postgresql")
JSONColumn = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Account(Base):
    """Chart of Accounts entry (COA)."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # asset | liability | equity | revenue | expense | cogs
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # asset/expense/cogs are debit-normal; liability/equity/revenue are credit-normal
    is_cash: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    bank_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    txn_date: Mapped[dt.date] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    # inflow = money received, outflow = money spent
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="manual")

    # AI classification result
    suggested_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # new | classified | needs_review | approved | posted | rejected
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    bank_account = relationship("Account", foreign_keys=[bank_account_id])
    suggested_account = relationship("Account", foreign_keys=[suggested_account_id])
    journal_entries = relationship(
        "JournalEntry", back_populates="transaction", cascade="all, delete-orphan"
    )


class JournalEntry(Base):
    """A single debit or credit line posted to the general ledger."""

    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    entry_date: Mapped[dt.date] = mapped_column(nullable=False)
    debit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    credit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    posted_by: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    transaction = relationship("Transaction", back_populates="journal_entries")
    account = relationship("Account")


class AiRun(Base):
    """Audit record of every AI decision (FR / AI Processing Rules: store AI run history)."""

    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, index=True
    )
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    engine: Mapped[str] = mapped_column(String(20), nullable=False)  # claude | rule-based
    input: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    output: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    """Immutable record of human + system actions (FR-HITL-1: 100% audit traceability)."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_value: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    new_value: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
