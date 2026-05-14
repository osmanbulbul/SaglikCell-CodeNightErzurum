from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.payment import PaymentHistory
from app.schemas.payment import PaymentUpgradeRequest, PaymentHistoryResponse

router = APIRouter()

@router.post("/upgrade", response_model=PaymentHistoryResponse)
async def upgrade_to_premium(
    *,
    db: AsyncSession = Depends(get_db),
    request: PaymentUpgradeRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Premium hesaba yükseltme simülasyonu. Paycell üzerinden ödeme yapılmış sayar.
    """
    if current_user.role == UserRole.premium_user:
        raise HTTPException(status_code=400, detail="User is already premium")
        
    payment = PaymentHistory(
        user_id=current_user.id,
        amount=99.99,
        currency="TRY",
        status="SUCCESS",
        payment_method=request.payment_method
    )
    db.add(payment)
    
    current_user.role = UserRole.premium_user
    db.add(current_user)
    
    await db.commit()
    await db.refresh(payment)
    return payment

@router.get("/history", response_model=List[PaymentHistoryResponse])
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Kullanıcının ödeme geçmişini getirir.
    """
    result = await db.execute(
        select(PaymentHistory)
        .where(PaymentHistory.user_id == current_user.id)
        .order_by(PaymentHistory.created_at.desc())
    )
    return list(result.scalars().all())

@router.delete("/subscription")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Premium aboneliği iptal etme simülasyonu.
    """
    if current_user.role != UserRole.premium_user:
        raise HTTPException(status_code=400, detail="User is not premium")
        
    current_user.role = UserRole.user
    db.add(current_user)
    
    payment = PaymentHistory(
        user_id=current_user.id,
        amount=0,
        currency="TRY",
        status="CANCELLED",
        payment_method="SYSTEM"
    )
    db.add(payment)
    
    await db.commit()
    return {"message": "Subscription cancelled successfully"}
