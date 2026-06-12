"""Seed the database with an organization, a Chart of Accounts, and sample
bank transactions so the platform is demoable immediately.

Run from the backend/ directory:  python -m app.seed
"""

import datetime as dt
import logging

from . import models
from .database import Base, SessionLocal, engine
from .logging_config import configure_logging

logger = logging.getLogger(__name__)

COA = [
    # code, name, type, is_cash
    ("1000", "Operating Bank Account", "asset", True),
    ("1010", "Accounts Receivable", "asset", False),
    ("1500", "Fixed Assets", "asset", False),
    ("2000", "Accounts Payable", "liability", False),
    ("2100", "Credit Card Payable", "liability", False),
    ("2500", "Loans Payable", "liability", False),
    ("3000", "Owner Equity", "equity", False),
    ("4000", "Product & Service Revenue", "revenue", False),
    ("4100", "Interest Income", "revenue", False),
    ("5000", "Payroll Expense", "expense", False),
    ("5100", "Rent Expense", "expense", False),
    ("5200", "Utilities Expense", "expense", False),
    ("5300", "Insurance Expense", "expense", False),
    ("5400", "Marketing Expense", "expense", False),
    ("5500", "Travel Expense", "expense", False),
    ("5600", "Software & Subscriptions", "expense", False),
    ("5700", "Professional Services", "expense", False),
    ("5900", "Other Expenses", "expense", False),
]

# Realistic-ish bank feed. Some are clear, some are deliberately ambiguous
# to exercise the human-in-the-loop review queue.
SAMPLE_TXNS = [
    ("2026-06-01", "ACME CORP INVOICE 1042 PAYMENT", 12500.00, "inflow"),
    ("2026-06-02", "GUSTO PAYROLL RUN", 8400.00, "outflow"),
    ("2026-06-02", "WeWork Monthly Rent - Suite 400", 3200.00, "outflow"),
    ("2026-06-03", "AWS CLOUD SERVICES", 1180.45, "outflow"),
    ("2026-06-04", "GOOGLE ADS", 950.00, "outflow"),
    ("2026-06-05", "DELTA AIR LINES 0061234567", 612.30, "outflow"),
    ("2026-06-06", "STATE FARM INSURANCE PREMIUM", 430.00, "outflow"),
    ("2026-06-07", "AMZN MKTPLACE US*2A4KD", 264.19, "outflow"),
    ("2026-06-08", "STRIPE PAYOUT", 4820.75, "inflow"),
    ("2026-06-09", "PG&E UTILITIES", 318.66, "outflow"),
    ("2026-06-10", "BAKER & MCKENZIE LLP RETAINER", 2750.00, "outflow"),
    ("2026-06-11", "SQ *BLUE BOTTLE COFFEE", 47.85, "outflow"),
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Organization).first():
            logger.info("Database already seeded — nothing to do.")
            return

        org = models.Organization(name="Northwind Trading Co.", base_currency="USD")
        db.add(org)
        db.flush()

        code_to_acct: dict[str, models.Account] = {}
        for code, name, atype, is_cash in COA:
            acct = models.Account(
                organization_id=org.id,
                code=code,
                name=name,
                account_type=atype,
                is_cash=is_cash,
            )
            db.add(acct)
            code_to_acct[code] = acct
        db.flush()

        bank = code_to_acct["1000"]
        for date_str, desc, amount, direction in SAMPLE_TXNS:
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
        logger.info(
            "Seeded org '%s' with %d accounts and %d transactions.",
            org.name,
            len(COA),
            len(SAMPLE_TXNS),
        )
    finally:
        db.close()


if __name__ == "__main__":
    configure_logging()
    run()
