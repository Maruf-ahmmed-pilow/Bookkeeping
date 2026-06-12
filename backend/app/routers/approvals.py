"""Human-in-the-Loop controls (FR-HITL-1).

Approving a transaction posts the balanced journal entries to the general ledger
and records full audit traceability. Rejecting sends it back out of the ledger.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..database import get_db

router = APIRouter(prefix="/api/transactions", tags=["approvals"])

_APPROVABLE = {"classified", "needs_review"}


@router.post("/{txn_id}/approve", response_model=schemas.TransactionDetail)
def approve(txn_id: str, decision: schemas.ApprovalDecision, db: Session = Depends(get_db)):
    txn = db.get(models.Transaction, txn_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")
    if txn.status not in _APPROVABLE:
        raise HTTPException(409, f"Cannot approve a transaction in status '{txn.status}'")

    # The reviewer may override the AI-suggested account.
    account_id = decision.account_id or txn.suggested_account_id
    if not account_id:
        raise HTTPException(422, "No account assigned — classify or choose one first")
    account = db.get(models.Account, account_id)
    if account is None or account.organization_id != txn.organization_id:
        raise HTTPException(422, "Invalid account")
    if account.is_cash:
        raise HTTPException(422, "Counterparty account cannot be the cash/bank account")

    previous = {"status": txn.status, "suggested_account_id": txn.suggested_account_id}
    services.post_journal_entries(db, txn, account, decision.actor)
    services.write_audit(
        db,
        txn.organization_id,
        decision.actor,
        "approve",
        "transaction",
        txn.id,
        previous,
        {"status": "posted", "account_id": account.id, "account_code": account.code},
        reason=decision.reason,
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.post("/{txn_id}/reject", response_model=schemas.TransactionDetail)
def reject(txn_id: str, decision: schemas.ApprovalDecision, db: Session = Depends(get_db)):
    txn = db.get(models.Transaction, txn_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")
    if txn.status == "posted":
        raise HTTPException(409, "Cannot reject a posted transaction")

    previous = {"status": txn.status}
    txn.status = "rejected"
    db.flush()
    services.write_audit(
        db,
        txn.organization_id,
        decision.actor,
        "reject",
        "transaction",
        txn.id,
        previous,
        {"status": "rejected"},
        reason=decision.reason,
    )
    db.commit()
    db.refresh(txn)
    return txn
