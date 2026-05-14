from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class DailyTrendPoint(BaseModel):
    date: date
    total_steps: float
    total_water: float
    sleep_hours: float
    total_calories: float
    weight: Optional[float] = None
    avg_heart_rate: Optional[float] = None

    class Config:
        from_attributes = True


class WeekComparisonResponse(BaseModel):
    """Bu hafta vs geçen hafta karşılaştırması."""
    metric: str
    this_week_total: float
    last_week_total: float
    change_percentage: float  # pozitif = artış, negatif = düşüş


class BmiDataPoint(BaseModel):
    date: date
    weight: float
    bmi: float
    category: str  # "Zayıf", "Normal", "Fazla Kilolu", "Obez"


class BmiHistoryResponse(BaseModel):
    height_cm: float
    current_bmi: Optional[float] = None
    current_category: Optional[str] = None
    history: List[BmiDataPoint]


class MealDistributionItem(BaseModel):
    meal_type: str  # "Kahvaltı", "Öğle", "Akşam", "Ara Öğün"
    total_calories: float
    percentage: float


class DashboardSummaryResponse(BaseModel):
    """Tek istekte tüm dashboard verisini döndürür (Task 5.5)."""
    today: Optional[DailyTrendPoint] = None
    weekly_trends: List[DailyTrendPoint]
    week_comparison: List[WeekComparisonResponse]
    current_bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    active_goals_count: int
    active_streaks: List[dict]
