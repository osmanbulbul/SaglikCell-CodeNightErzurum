from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

class GoalCreate(BaseModel):
    goal_type: str = Field(..., description="'daily_steps', 'weekly_water', 'daily_calories' vb.")
    target_value: float = Field(..., gt=0)
    expires_at: Optional[datetime] = None

class GoalResponse(BaseModel):
    id: UUID
    user_id: UUID
    goal_type: str
    target_value: float
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class GoalProgressResponse(BaseModel):
    id: UUID
    goal_id: UUID
    user_id: UUID
    date: date
    current_value: float
    progress_percentage: float
    is_completed: bool

    class Config:
        from_attributes = True

class StreakResponse(BaseModel):
    id: UUID
    user_id: UUID
    streak_type: str
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date] = None

    class Config:
        from_attributes = True
