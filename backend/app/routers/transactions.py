from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..database import get_db

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _default_bank(db: Session, org_id: str) -> models.Account:
    bank = (
        db.query(models.Account)
        .filter(
            models.Account.organization_id == org_id,
            models.Account.is_cash.is_(True),
        )
        .order_by(models.Account.code)
        .first()
    )
    if bank is None:
        raise HTTPException(500, "No cash account configured — run the seed script.")
    return bank


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    org = services.get_default_org(db)
    q = db.query(models.Transaction).filter(models.Transaction.organization_id == org.id)
    if status:
        q = q.filter(models.Transaction.status == status)
    return q.order_by(models.Transaction.created_at.desc()).all()


@router.post("", response_model=schemas.TransactionDetail, status_code=201)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    org = services.get_default_org(db)
    if payload.direction not in ("inflow", "outflow"):
        raise HTTPException(422, "direction must be 'inflow' or 'outflow'")
    if payload.amount <= 0:
        raise HTTPException(422, "amount must be positive")

    bank_id = payload.bank_account_id or _default_bank(db, org.id).id
    txn = models.Transaction(
        organization_id=org.id,
        bank_account_id=bank_id,
        txn_date=payload.txn_date,
        description=payload.description,
        amount=payload.amount,
        direction=payload.direction,
        source_system="manual",
        status="new",
    )
    db.add(txn)
    db.flush()
    services.write_audit(
        db, org.id, "system", "create", "transaction", txn.id, {}, {"status": "new"}
    )
    db.commit()
    db.refresh(txn)
    return txn


@router.get("/{txn_id}", response_model=schemas.TransactionDetail)
def get_transaction(txn_id: str, db: Session = Depends(get_db)):
    txn = db.get(models.Transaction, txn_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")
    return txn


@router.post("/{txn_id}/classify", response_model=schemas.ClassifyResult)
def classify_transaction(txn_id: str, db: Session = Depends(get_db)):
    """Run the AI Classification Agent on a single transaction (F2)."""
    txn = db.get(models.Transaction, txn_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")
    if txn.status == "posted":
        raise HTTPException(409, "Transaction already posted")

    result = services.classify_transaction(db, txn)
    db.commit()
    db.refresh(txn)

    account = db.get(models.Account, txn.suggested_account_id) if txn.suggested_account_id else None
    return schemas.ClassifyResult(
        transaction_id=txn.id,
        account_code=result.account_code,
        account_name=account.name if account else "(unrecognised)",
        confidence=result.confidence,
        reasoning=result.reasoning,
        engine=result.engine,
        status=txn.status,
    )


@router.post("/classify-all")
def classify_all_new(db: Session = Depends(get_db)):
    """Batch-classify every transaction still in 'new' status."""
    org = services.get_default_org(db)
    pending = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.organization_id == org.id,
            models.Transaction.status == "new",
        )
        .all()
    )
    for txn in pending:
        services.classify_transaction(db, txn)
    db.commit()
    return {"classified": len(pending)}
