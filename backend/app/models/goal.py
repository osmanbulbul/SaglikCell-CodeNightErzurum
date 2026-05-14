import uuid
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base_class import Base

class Goal(Base):
    __tablename__ = "goals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    goal_type = Column(String, nullable=False) # 'daily_steps', 'weekly_water' vs
    target_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

class GoalProgress(Base):
    __tablename__ = "goal_progress"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    current_value = Column(Float, default=0)
    progress_percentage = Column(Float, default=0)
    is_completed = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Streak(Base):
    __tablename__ = "streaks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    streak_type = Column(String, nullable=False) # 'login', 'daily_steps_goal' vb
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
