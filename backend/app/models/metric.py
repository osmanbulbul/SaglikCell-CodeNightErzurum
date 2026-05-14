import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base_class import Base

class Metric(Base):
    __tablename__ = "metrics"
    # id string will be generated natively or by timescale if needed, but uuid is fine
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    metric_type = Column(String, nullable=False) # 'steps', 'water', 'sleep'
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), primary_key=True, default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_metrics_user_time', 'user_id', 'timestamp'),
    )

class DailySummary(Base):
    __tablename__ = "daily_summary"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False) # Midnight of that day
    total_steps = Column(Float, default=0)
    total_water = Column(Float, default=0)
    sleep_hours = Column(Float, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uix_user_date_summary'),
    )
