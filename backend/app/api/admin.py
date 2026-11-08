from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth import require_admin
from backend.app.core.database import get_db
from backend.app.models import SupplierOffer, User
from backend.app.schemas import SupplierOfferCreate, SupplierOfferResponse

router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


@router.get("/supplier-offers", response_model=list[SupplierOfferResponse])
def list_supplier_offers(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[SupplierOffer]:
    return list(db.scalars(select(SupplierOffer).order_by(SupplierOffer.id.desc())).all())


@router.post(
    "/supplier-offers",
    response_model=SupplierOfferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier_offer(
    payload: SupplierOfferCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SupplierOffer:
    if payload.is_active and payload.contract_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An offer cannot be activated before its commercial contract is verified",
        )
    offer = SupplierOffer(**payload.model_dump(), created_by=admin.id)
    db.add(offer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supplier offer with this identity already exists",
        ) from None
    db.refresh(offer)
    return offer
