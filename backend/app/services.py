"""Domain services: classification orchestration + double-entry posting."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from . import models
from .ai import classifier
from .config import settings

logger = logging.getLogger(__name__)


def get_default_org(db: Session) -> models.Organization:
    org = db.query(models.Organization).first()
    if org is None:
        raise RuntimeError("No organization found — run the seed script.")
    return org


def coa_options(db: Session, org_id: str) -> list[classifier.CoaOption]:
    """Non-cash accounts the classifier may assign to."""
    accounts = (
        db.query(models.Account)
        .filter(
            models.Account.organization_id == org_id,
            models.Account.is_active.is_(True),
            models.Account.is_cash.is_(False),
        )
        .order_by(models.Account.code)
        .all()
    )
    return [
        classifier.CoaOption(code=a.code, name=a.name, account_type=a.account_type)
        for a in accounts
    ]


def classify_transaction(db: Session, txn: models.Transaction) -> classifier.ClassificationOutput:
    """Run the classification agent and apply the human-in-the-loop confidence gate."""
    org_id = txn.organization_id
    options = coa_options(db, org_id)
    result = classifier.classify(txn.description, float(txn.amount), txn.direction, options)

    account = (
        db.query(models.Account)
        .filter(
            models.Account.organization_id == org_id,
            models.Account.code == result.account_code,
        )
        .first()
    )

    txn.suggested_account_id = account.id if account else None
    txn.confidence = result.confidence
    txn.ai_reasoning = result.reasoning

    # FR-HITL-1 / Quality Control Agent escalation: anything below the configured
    # confidence threshold (or an unrecognised account) goes to human review.
    if account is not None and result.confidence >= settings.confidence_threshold:
        txn.status = "classified"
    else:
        txn.status = "needs_review"

    logger.info(
        "Classified transaction %s via %s engine: account=%s confidence=%.2f status=%s",
        txn.id,
        result.engine,
        result.account_code,
        result.confidence,
        txn.status,
    )

    db.add(
        models.AiRun(
            organization_id=org_id,
            agent="classification",
            transaction_id=txn.id,
            model=settings.ai_model,
            engine=result.engine,
            input={
                "description": txn.description,
                "amount": float(txn.amount),
                "direction": txn.direction,
            },
            output={
                "account_code": result.account_code,
                "reasoning": result.reasoning,
            },
            confidence=result.confidence,
        )
    )
    db.flush()
    return result


def post_journal_entries(
    db: Session, txn: models.Transaction, account: models.Account, actor: str
) -> None:
    """Create the balanced debit/credit pair and post to the general ledger."""
    amount = float(txn.amount)
    bank = txn.bank_account

    if txn.direction == "outflow":
        debit_acct, credit_acct = account, bank
    else:  # inflow
        debit_acct, credit_acct = bank, account

    db.add(
        models.JournalEntry(
            organization_id=txn.organization_id,
            transaction_id=txn.id,
            account_id=debit_acct.id,
            entry_date=txn.txn_date,
            debit=amount,
            credit=0,
            description=txn.description,
            posted_by=actor,
        )
    )
    db.add(
        models.JournalEntry(
            organization_id=txn.organization_id,
            transaction_id=txn.id,
            account_id=credit_acct.id,
            entry_date=txn.txn_date,
            debit=0,
            credit=amount,
            description=txn.description,
            posted_by=actor,
        )
    )
    txn.suggested_account_id = account.id
    txn.status = "posted"
    db.flush()
    logger.info(
        "Posted transaction %s to ledger: debit=%s credit=%s amount=%.2f actor=%s",
        txn.id,
        debit_acct.code,
        credit_acct.code,
        amount,
        actor,
    )


def write_audit(
    db: Session,
    org_id: str,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    previous_value: dict,
    new_value: dict,
    reason: str = "",
) -> None:
    db.add(
        models.AuditLog(
            organization_id=org_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
        )
    )
    db.flush()
