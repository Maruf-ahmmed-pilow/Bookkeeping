from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..database import get_db

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[schemas.AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    org = services.get_default_org(db)
    return (
        db.query(models.Account)
        .filter(models.Account.organization_id == org.id)
        .order_by(models.Account.code)
        .all()
    )
