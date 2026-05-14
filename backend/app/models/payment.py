import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base_class import Base

class PaymentHistory(Base):
    __tablename__ = "payment_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="TRY")
    status = Column(String, nullable=False) # e.g., 'SUCCESS', 'FAILED'
    payment_method = Column(String) # e.g., 'PAYCELL', 'CREDIT_CARD'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
