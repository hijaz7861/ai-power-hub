from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.api.auth import get_current_user
from backend.app.core.database import get_db
from backend.app.models import CreditLedger, User
from backend.app.schemas import CreditBalanceResponse, CreditLedgerEntryResponse
from backend.app.services.credits import get_balance

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])

@router.get("/balance", response_model=CreditBalanceResponse)
def balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CreditBalanceResponse:
    return CreditBalanceResponse(balance=get_balance(db, user.id))


@router.get("/ledger", response_model=list[CreditLedgerEntryResponse])
def ledger(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CreditLedger]:
    statement = (
        select(CreditLedger)
        .where(CreditLedger.user_id == user.id)
        .order_by(CreditLedger.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())
