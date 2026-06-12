"""Financial Reporting (F8 / FR-RPT-1..3) built from posted journal entries."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _balances(db: Session, org_id: str) -> dict[str, dict]:
    """Net debit/credit per account from posted journal entries."""
    rows = (
        db.query(
            models.Account.id,
            models.Account.code,
            models.Account.name,
            models.Account.account_type,
            models.Account.is_cash,
            func.coalesce(func.sum(models.JournalEntry.debit), 0).label("debit"),
            func.coalesce(func.sum(models.JournalEntry.credit), 0).label("credit"),
        )
        .join(models.JournalEntry, models.JournalEntry.account_id == models.Account.id)
        .filter(models.Account.organization_id == org_id)
        .group_by(models.Account.id)
        .all()
    )
    out: dict[str, dict] = {}
    for r in rows:
        out[r.code] = {
            "code": r.code,
            "name": r.name,
            "type": r.account_type,
            "is_cash": r.is_cash,
            "debit": float(r.debit),
            "credit": float(r.credit),
        }
    return out


@router.get("/profit-and-loss", response_model=schemas.ProfitAndLoss)
def profit_and_loss(db: Session = Depends(get_db)):
    org = services.get_default_org(db)
    bals = _balances(db, org.id)

    revenue, expenses = [], []
    for b in bals.values():
        if b["type"] == "revenue":
            amt = b["credit"] - b["debit"]
            if amt:
                revenue.append(schemas.ReportLine(code=b["code"], name=b["name"], amount=amt))
        elif b["type"] in ("expense", "cogs"):
            amt = b["debit"] - b["credit"]
            if amt:
                expenses.append(schemas.ReportLine(code=b["code"], name=b["name"], amount=amt))

    revenue.sort(key=lambda x: x.code)
    expenses.sort(key=lambda x: x.code)
    total_rev = sum(x.amount for x in revenue)
    total_exp = sum(x.amount for x in expenses)
    return schemas.ProfitAndLoss(
        revenue=revenue,
        expenses=expenses,
        total_revenue=round(total_rev, 2),
        total_expenses=round(total_exp, 2),
        net_income=round(total_rev - total_exp, 2),
    )


@router.get("/balance-sheet", response_model=schemas.BalanceSheet)
def balance_sheet(db: Session = Depends(get_db)):
    org = services.get_default_org(db)
    bals = _balances(db, org.id)

    assets, liabilities, equity = [], [], []
    net_income = 0.0
    for b in bals.values():
        if b["type"] == "asset":
            amt = b["debit"] - b["credit"]
            if amt:
                assets.append(schemas.ReportLine(code=b["code"], name=b["name"], amount=amt))
        elif b["type"] == "liability":
            amt = b["credit"] - b["debit"]
            if amt:
                liabilities.append(schemas.ReportLine(code=b["code"], name=b["name"], amount=amt))
        elif b["type"] == "equity":
            amt = b["credit"] - b["debit"]
            if amt:
                equity.append(schemas.ReportLine(code=b["code"], name=b["name"], amount=amt))
        elif b["type"] == "revenue":
            net_income += b["credit"] - b["debit"]
        elif b["type"] in ("expense", "cogs"):
            net_income -= b["debit"] - b["credit"]

    # Current-period earnings roll into equity so the sheet balances.
    if round(net_income, 2):
        equity.append(
            schemas.ReportLine(
                code="3900",
                name="Current Period Earnings",
                amount=round(net_income, 2),
            )
        )

    assets.sort(key=lambda x: x.code)
    liabilities.sort(key=lambda x: x.code)
    equity.sort(key=lambda x: x.code)
    total_assets = round(sum(x.amount for x in assets), 2)
    total_liab = round(sum(x.amount for x in liabilities), 2)
    total_equity = round(sum(x.amount for x in equity), 2)
    return schemas.BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=total_assets,
        total_liabilities=total_liab,
        total_equity=total_equity,
        balanced=abs(total_assets - (total_liab + total_equity)) < 0.01,
    )


@router.get("/dashboard", response_model=schemas.DashboardMetrics)
def dashboard(db: Session = Depends(get_db)):
    org = services.get_default_org(db)
    bals = _balances(db, org.id)

    total_rev = total_exp = cash = 0.0
    for b in bals.values():
        if b["type"] == "revenue":
            total_rev += b["credit"] - b["debit"]
        elif b["type"] in ("expense", "cogs"):
            total_exp += b["debit"] - b["credit"]
        if b["is_cash"]:
            cash += b["debit"] - b["credit"]

    pending = (
        db.query(func.count(models.Transaction.id))
        .filter(
            models.Transaction.organization_id == org.id,
            models.Transaction.status == "needs_review",
        )
        .scalar()
    )
    posted = (
        db.query(func.count(models.Transaction.id))
        .filter(
            models.Transaction.organization_id == org.id,
            models.Transaction.status == "posted",
        )
        .scalar()
    )
    return schemas.DashboardMetrics(
        total_revenue=round(total_rev, 2),
        total_expenses=round(total_exp, 2),
        net_income=round(total_rev - total_exp, 2),
        cash_on_hand=round(cash, 2),
        pending_review=int(pending or 0),
        posted_transactions=int(posted or 0),
    )
