from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.auth import get_current_user
from backend.app.core.database import get_db
from backend.app.models import User
from backend.app.schemas import CreditBalanceResponse
from backend.app.services.credits import get_balance

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])

@router.get("/balance", response_model=CreditBalanceResponse)
def balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CreditBalanceResponse:
    return CreditBalanceResponse(balance=get_balance(db, user.id))
