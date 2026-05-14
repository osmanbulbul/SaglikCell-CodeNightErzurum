from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class MetricCreate(BaseModel):
    metric_type: str = Field(..., description="'steps', 'water', 'sleep', 'weight', 'heart_rate', 'calories'")
    value: float = Field(..., gt=0, description="Value of the metric")
    timestamp: Optional[datetime] = None

class MetricResponse(BaseModel):
    id: UUID
    user_id: UUID
    metric_type: str
    value: float
    timestamp: datetime

    class Config:
        from_attributes = True

class DailySummaryResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: datetime
    total_steps: float
    total_water: float
    sleep_hours: float
    total_calories: float
    weight: Optional[float] = None
    avg_heart_rate: Optional[float] = None
    updated_at: datetime

    class Config:
        from_attributes = True
