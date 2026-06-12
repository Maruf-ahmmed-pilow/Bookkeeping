import datetime as dt

from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    account_type: str
    is_cash: bool
    is_active: bool


class TransactionCreate(BaseModel):
    bank_account_id: str | None = None  # defaults to the seeded operating bank account
    txn_date: dt.date
    description: str
    amount: float
    direction: str  # inflow | outflow


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    txn_date: dt.date
    description: str
    amount: float
    direction: str
    status: str
    source_system: str
    confidence: float | None
    ai_reasoning: str | None
    suggested_account_id: str | None
    bank_account_id: str
    created_at: dt.datetime


class TransactionDetail(TransactionOut):
    suggested_account: AccountOut | None = None
    bank_account: AccountOut | None = None


class ClassifyResult(BaseModel):
    transaction_id: str
    account_code: str
    account_name: str
    confidence: float
    reasoning: str
    engine: str
    status: str  # classified | needs_review


class ApprovalDecision(BaseModel):
    # optional override of the AI-suggested account when approving
    account_id: str | None = None
    reason: str = ""
    actor: str = "bookkeeper"


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    account_id: str
    entry_date: dt.date
    debit: float
    credit: float
    description: str
    posted_by: str


class ReportLine(BaseModel):
    code: str
    name: str
    amount: float


class ProfitAndLoss(BaseModel):
    revenue: list[ReportLine]
    expenses: list[ReportLine]
    total_revenue: float
    total_expenses: float
    net_income: float


class BalanceSheet(BaseModel):
    assets: list[ReportLine]
    liabilities: list[ReportLine]
    equity: list[ReportLine]
    total_assets: float
    total_liabilities: float
    total_equity: float
    balanced: bool


class DashboardMetrics(BaseModel):
    total_revenue: float
    total_expenses: float
    net_income: float
    cash_on_hand: float
    pending_review: int
    posted_transactions: int
