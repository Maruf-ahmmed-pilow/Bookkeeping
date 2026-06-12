"""Shared pytest fixtures.

The suite runs entirely offline against an in-memory SQLite database — no
PostgreSQL and no ``ANTHROPIC_API_KEY`` required — so it exercises the
rule-based classification engine and the full intake → approval → reporting
flow deterministically.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import get_db
from app.main import app


@pytest.fixture()
def db_session() -> Iterator[Session]:
    """A fresh, isolated in-memory database per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        _seed(session)
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """A TestClient whose ``get_db`` dependency is bound to the test session."""

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


_COA = [
    ("1000", "Operating Bank Account", "asset", True),
    ("2000", "Accounts Payable", "liability", False),
    ("3000", "Owner Equity", "equity", False),
    ("4000", "Product & Service Revenue", "revenue", False),
    ("5000", "Payroll Expense", "expense", False),
    ("5600", "Software & Subscriptions", "expense", False),
    ("5900", "Other Expenses", "expense", False),
]

_TXNS = [
    ("2026-06-01", "ACME CORP INVOICE PAYMENT", 12500.00, "inflow"),
    ("2026-06-02", "GUSTO PAYROLL RUN", 8400.00, "outflow"),
    ("2026-06-03", "AWS CLOUD SERVICES", 1180.45, "outflow"),
    ("2026-06-07", "AMZN MKTPLACE US*2A4KD", 264.19, "outflow"),
]


def _seed(db: Session) -> None:
    org = models.Organization(name="Test Co.", base_currency="USD")
    db.add(org)
    db.flush()

    bank = None
    for code, name, atype, is_cash in _COA:
        acct = models.Account(
            organization_id=org.id,
            code=code,
            name=name,
            account_type=atype,
            is_cash=is_cash,
        )
        db.add(acct)
        if is_cash:
            bank = acct
    db.flush()

    for date_str, desc, amount, direction in _TXNS:
        db.add(
            models.Transaction(
                organization_id=org.id,
                bank_account_id=bank.id,
                txn_date=dt.date.fromisoformat(date_str),
                description=desc,
                amount=amount,
                direction=direction,
                source_system="bank_feed",
                status="new",
            )
        )
    db.commit()
