from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class PaymentUpgradeRequest(BaseModel):
    payment_method: str = "PAYCELL"

class PaymentHistoryResponse(BaseModel):
    id: UUID
    amount: float
    currency: str
    status: str
    payment_method: str
    created_at: datetime

    class Config:
        from_attributes = True
