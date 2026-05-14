"""
FAZ 5: Analitik, Görselleştirme ve Rapor Export
Endpoint'ler:
  GET /analytics/trends              - Haftalık/aylık trend (5.1)
  GET /analytics/compare             - Bu hafta vs geçen hafta (5.2)
  GET /analytics/bmi                 - BMI ve tarihsel seri (5.3)
  GET /analytics/meals/distribution  - Öğün kalori dağılımı (5.4)
  GET /analytics/dashboard           - Tek istekte dashboard özeti (5.5)
  GET /analytics/report              - PDF/CSV export (5.6)
"""

import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.models.metric import DailySummary, Metric
from app.models.goal import Goal, Streak
from app.schemas.analytics import (
    DailyTrendPoint,
    WeekComparisonResponse,
    BmiHistoryResponse,
    BmiDataPoint,
    MealDistributionItem,
    DashboardSummaryResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Yardımcı: BMI Hesaplama
# ---------------------------------------------------------------------------
def _calc_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    if height_cm <= 0:
        return 0.0, "Bilinmiyor"
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category = "Zayıf"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Fazla Kilolu"
    else:
        category = "Obez"
    return bmi, category


# ---------------------------------------------------------------------------
# 5.1 – Haftalık / Aylık Trend
# ---------------------------------------------------------------------------
@router.get("/trends", response_model=List[DailyTrendPoint])
async def get_trends(
    period: Literal["weekly", "monthly"] = Query("weekly", description="'weekly' (7 gün) veya 'monthly' (30 gün)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Kullanıcının haftalık (7 gün) veya aylık (30 gün) metrik trend verisini döndürür.
    Kaynak: daily_summary tablosu (optimize edilmiş okuma). (Task 5.1 & 5.7)
    """
    days = 7 if period == "weekly" else 30
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.date >= since)
        .order_by(DailySummary.date.asc())
    )
    rows = result.scalars().all()
    return [DailyTrendPoint.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# 5.2 – Bu Hafta vs Geçen Hafta Karşılaştırması
# ---------------------------------------------------------------------------
@router.get("/compare", response_model=List[WeekComparisonResponse])
async def compare_weeks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Bu haftanın toplam metriklerini geçen haftayla karşılaştırır. (Task 5.2)
    """
    now = datetime.now(timezone.utc)
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)

    # Bu hafta
    tw_result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.date >= this_week_start)
    )
    this_week_rows = tw_result.scalars().all()

    # Geçen hafta
    lw_result = await db.execute(
        select(DailySummary)
        .where(
            DailySummary.user_id == current_user.id,
            DailySummary.date >= last_week_start,
            DailySummary.date < this_week_start,
        )
    )
    last_week_rows = lw_result.scalars().all()

    def _sum(rows, field: str) -> float:
        return sum(getattr(r, field) or 0 for r in rows)

    def _pct_change(tw: float, lw: float) -> float:
        if lw == 0:
            return 100.0 if tw > 0 else 0.0
        return round((tw - lw) / lw * 100, 1)

    metrics = ["total_steps", "total_water", "sleep_hours", "total_calories"]
    labels = {"total_steps": "Adım", "total_water": "Su (ml)", "sleep_hours": "Uyku (saat)", "total_calories": "Kalori"}

    return [
        WeekComparisonResponse(
            metric=labels[m],
            this_week_total=round(_sum(this_week_rows, m), 2),
            last_week_total=round(_sum(last_week_rows, m), 2),
            change_percentage=_pct_change(_sum(this_week_rows, m), _sum(last_week_rows, m)),
        )
        for m in metrics
    ]


# ---------------------------------------------------------------------------
# 5.3 – BMI Hesaplama ve Tarihsel Seri
# ---------------------------------------------------------------------------
@router.get("/bmi", response_model=BmiHistoryResponse)
async def get_bmi_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Kullanıcının günlük kilo girişlerinden BMI tarihsel serisini hesaplar. (Task 5.3)
    Boy bilgisi kullanıcı profilinden alınır.
    """
    height_cm = current_user.height or 0

    # Kilo girişi olan günlük özet kayıtlarını al
    result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.weight != None)
        .order_by(DailySummary.date.asc())
        .limit(90)  # Son 90 gün
    )
    rows = result.scalars().all()

    history: List[BmiDataPoint] = []
    for row in rows:
        if row.weight and height_cm > 0:
            bmi_val, category = _calc_bmi(row.weight, height_cm)
            history.append(BmiDataPoint(
                date=row.date if isinstance(row.date, date) else row.date.date(),
                weight=row.weight,
                bmi=bmi_val,
                category=category,
            ))

    current_bmi, current_category = None, None
    if history:
        current_bmi = history[-1].bmi
        current_category = history[-1].category

    return BmiHistoryResponse(
        height_cm=height_cm,
        current_bmi=current_bmi,
        current_category=current_category,
        history=history,
    )


# ---------------------------------------------------------------------------
# 5.4 – Öğün Kalori Dağılımı
# ---------------------------------------------------------------------------
@router.get("/meals/distribution", response_model=List[MealDistributionItem])
async def get_meal_distribution(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Son N günlük kalori metriklerini öğün tiplerine göre dağıtır. (Task 5.4)
    Android, metric_type'ı 'calories_breakfast', 'calories_lunch' vb. şeklinde gönderir.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Metric)
        .where(
            Metric.user_id == current_user.id,
            Metric.metric_type.like("calories_%"),
            Metric.timestamp >= since,
        )
    )
    rows = result.scalars().all()

    label_map = {
        "calories_breakfast": "Kahvaltı",
        "calories_lunch": "Öğle",
        "calories_dinner": "Akşam",
        "calories_snack": "Ara Öğün",
    }

    totals: dict[str, float] = {v: 0.0 for v in label_map.values()}
    for row in rows:
        label = label_map.get(row.metric_type)
        if label:
            totals[label] += row.value

    grand_total = sum(totals.values()) or 1  # sıfıra bölünmeyi önle

    return [
        MealDistributionItem(
            meal_type=meal,
            total_calories=round(cal, 2),
            percentage=round(cal / grand_total * 100, 1),
        )
        for meal, cal in totals.items()
    ]


# ---------------------------------------------------------------------------
# 5.5 – Dashboard Özet (tek istekte)
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Android ana ekranı için tek istekte tüm özet verileri döndürür. (Task 5.5)
    """
    # Bugünün özeti
    today_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.date >= today_dt)
    )
    today_row = today_result.scalars().first()
    today_data = DailyTrendPoint.model_validate(today_row) if today_row else None

    # Son 7 gün trendi
    since_7 = datetime.now(timezone.utc) - timedelta(days=7)
    trends_result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.date >= since_7)
        .order_by(DailySummary.date.asc())
    )
    weekly_trends = [DailyTrendPoint.model_validate(r) for r in trends_result.scalars().all()]

    # Bu hafta vs geçen hafta (adım ve su)
    this_week_start = datetime.now(timezone.utc) - timedelta(days=7)
    last_week_start = datetime.now(timezone.utc) - timedelta(days=14)

    tw_r = await db.execute(select(DailySummary).where(DailySummary.user_id == current_user.id, DailySummary.date >= this_week_start))
    lw_r = await db.execute(select(DailySummary).where(DailySummary.user_id == current_user.id, DailySummary.date >= last_week_start, DailySummary.date < this_week_start))
    tw_rows, lw_rows = tw_r.scalars().all(), lw_r.scalars().all()

    def _sum(rows, f): return sum(getattr(r, f) or 0 for r in rows)
    def _pct(tw, lw): return round((tw - lw) / lw * 100, 1) if lw else (100.0 if tw else 0.0)

    week_comparison = [
        WeekComparisonResponse(metric="Adım", this_week_total=_sum(tw_rows, "total_steps"), last_week_total=_sum(lw_rows, "total_steps"), change_percentage=_pct(_sum(tw_rows, "total_steps"), _sum(lw_rows, "total_steps"))),
        WeekComparisonResponse(metric="Su (ml)", this_week_total=_sum(tw_rows, "total_water"), last_week_total=_sum(lw_rows, "total_water"), change_percentage=_pct(_sum(tw_rows, "total_water"), _sum(lw_rows, "total_water"))),
    ]

    # BMI
    current_bmi, current_category = None, None
    if today_row and today_row.weight and current_user.height:
        current_bmi, current_category = _calc_bmi(today_row.weight, current_user.height)

    # Aktif hedef sayısı
    goals_count_r = await db.execute(select(func.count(Goal.id)).where(Goal.user_id == current_user.id, Goal.is_active == True))
    active_goals_count = goals_count_r.scalar() or 0

    # Aktif streak'ler
    streaks_r = await db.execute(select(Streak).where(Streak.user_id == current_user.id, Streak.current_streak > 0))
    active_streaks = [{"type": s.streak_type, "current": s.current_streak, "longest": s.longest_streak} for s in streaks_r.scalars().all()]

    return DashboardSummaryResponse(
        today=today_data,
        weekly_trends=weekly_trends,
        week_comparison=week_comparison,
        current_bmi=current_bmi,
        bmi_category=current_category,
        active_goals_count=active_goals_count,
        active_streaks=active_streaks,
    )


# ---------------------------------------------------------------------------
# 5.6 – Rapor Export (PDF / CSV)
# ---------------------------------------------------------------------------
@router.get("/report")
async def export_report(
    period: Literal["weekly", "monthly"] = Query("weekly"),
    format: Literal["pdf", "csv"] = Query("csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Kullanıcının haftalık veya aylık sağlık raporunu PDF ya da CSV olarak indirir. (Task 5.6)
    """
    days = 7 if period == "weekly" else 30
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.date >= since)
        .order_by(DailySummary.date.asc())
    )
    rows = result.scalars().all()

    period_label = "Haftalık" if period == "weekly" else "Aylık"
    filename = f"saglikcell_{period}_rapor"

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Tarih", "Adım", "Su (ml)", "Uyku (saat)", "Kalori", "Kilo (kg)", "Ortalama Nabız"])
        for row in rows:
            row_date = row.date.date() if hasattr(row.date, "date") else row.date
            writer.writerow([
                row_date,
                round(row.total_steps or 0, 1),
                round(row.total_water or 0, 1),
                round(row.sleep_hours or 0, 2),
                round(row.total_calories or 0, 1),
                row.weight or "-",
                round(row.avg_heart_rate, 1) if row.avg_heart_rate else "-",
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.read()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    # PDF
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF kütüphanesi yüklenemedi.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"SağlıkCell – {period_label} Sağlık Raporu", styles["Title"]))
    elements.append(Paragraph(f"Kullanıcı: {current_user.full_name or current_user.phone_number}", styles["Normal"]))
    elements.append(Paragraph(f"Oluşturma Tarihi: {date.today()}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    header = ["Tarih", "Adım", "Su (ml)", "Uyku", "Kalori", "Kilo", "Nabız"]
    data = [header]
    for row in rows:
        row_date = row.date.date() if hasattr(row.date, "date") else row.date
        data.append([
            str(row_date),
            str(round(row.total_steps or 0, 0)),
            str(round(row.total_water or 0, 0)),
            f"{round(row.sleep_hours or 0, 1)}s",
            str(round(row.total_calories or 0, 0)),
            f"{row.weight} kg" if row.weight else "-",
            f"{round(row.avg_heart_rate, 0)} bpm" if row.avg_heart_rate else "-",
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
    )
