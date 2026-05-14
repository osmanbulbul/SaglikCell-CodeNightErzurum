import asyncio
from datetime import datetime, timezone
from typing import Any, List, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.metric import Metric, DailySummary
from app.schemas.metric import MetricCreate, MetricResponse, DailySummaryResponse

router = APIRouter()

# Global sözlük: Kullanıcıların arka plan simülasyon durumlarını tutar.
# Gerçek prodüksiyon ortamında Redis kullanılabilir, simülasyon için yeterlidir.
active_simulations: Dict[UUID, bool] = {}

async def simulate_steps_task(user_id: UUID):
    """
    Arka planda her 5 saniyede bir 100 adım ekleyen simülatör görevi (Task 3.5).
    """
    while active_simulations.get(user_id, False):
        async with AsyncSessionLocal() as db:
            # 1. Metriği Ekle
            new_metric = Metric(
                user_id=user_id,
                metric_type="steps",
                value=100.0,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(new_metric)
            
            # 2. Günlük Özeti Güncelle
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            result = await db.execute(
                select(DailySummary)
                .where(DailySummary.user_id == user_id, DailySummary.date == today)
            )
            summary = result.scalars().first()
            
            if not summary:
                summary = DailySummary(
                    user_id=user_id,
                    date=today,
                    total_steps=100.0
                )
                db.add(summary)
            else:
                summary.total_steps += 100.0
                
            await db.commit()
            
        await asyncio.sleep(5)


@router.post("/", response_model=MetricResponse)
async def create_metric(
    *,
    db: AsyncSession = Depends(get_db),
    metric_in: MetricCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Yeni bir sağlık metriği kaydeder, anomali kontrolü yapar ve günlük özeti otomatik günceller. (Task 3.1 & 3.2)
    """
    # Anomali Validasyonu
    if metric_in.metric_type == "steps" and metric_in.value > 50000:
        raise HTTPException(status_code=400, detail="Anomali Tespit Edildi: Tek seferde 50.000'den fazla adım girilemez.")
    if metric_in.metric_type == "water" and metric_in.value > 10000:
        raise HTTPException(status_code=400, detail="Anomali Tespit Edildi: Tek seferde 10.000 ml'den fazla su girilemez.")

    metric_time = metric_in.timestamp or datetime.now(timezone.utc)
    
    new_metric = Metric(
        user_id=current_user.id,
        metric_type=metric_in.metric_type,
        value=metric_in.value,
        timestamp=metric_time
    )
    db.add(new_metric)

    # Günlük Özeti Güncelle
    today = metric_time.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id, DailySummary.date == today)
    )
    summary = result.scalars().first()

    if not summary:
        summary = DailySummary(
            user_id=current_user.id,
            date=today,
            total_steps=0,
            total_water=0,
            sleep_hours=0
        )
        db.add(summary)

    if metric_in.metric_type == "steps":
        summary.total_steps += metric_in.value
    elif metric_in.metric_type == "water":
        summary.total_water += metric_in.value
    elif metric_in.metric_type == "sleep":
        summary.sleep_hours += metric_in.value

    await db.commit()
    await db.refresh(new_metric)
    return new_metric


@router.get("/summary", response_model=List[DailySummaryResponse])
async def get_daily_summaries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
    limit: int = 7
) -> Any:
    """
    Kullanıcının son N günlük özet verilerini getirir (Dashboard için).
    """
    result = await db.execute(
        select(DailySummary)
        .where(DailySummary.user_id == current_user.id)
        .order_by(DailySummary.date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.delete("/{metric_id}")
async def delete_metric(
    metric_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Geçmiş bir metrik kaydını siler ve günlük özeti düzeltir. (Task 3.3)
    """
    result = await db.execute(
        select(Metric).where(Metric.id == metric_id, Metric.user_id == current_user.id)
    )
    metric = result.scalars().first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Metrik bulunamadı.")
        
    # Günlük özetten bu değeri çıkar
    today = metric.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    summary_result = await db.execute(
        select(DailySummary).where(DailySummary.user_id == current_user.id, DailySummary.date == today)
    )
    summary = summary_result.scalars().first()
    
    if summary:
        if metric.metric_type == "steps":
            summary.total_steps = max(0, summary.total_steps - metric.value)
        elif metric.metric_type == "water":
            summary.total_water = max(0, summary.total_water - metric.value)
        elif metric.metric_type == "sleep":
            summary.sleep_hours = max(0, summary.sleep_hours - metric.value)
            
    await db.delete(metric)
    await db.commit()
    return {"message": "Metrik başarıyla silindi ve günlük özet güncellendi."}


@router.post("/simulate/steps/start")
async def start_step_simulation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Arka planda adım simülasyonunu başlatır. (Task 3.5)
    """
    if active_simulations.get(current_user.id, False):
        raise HTTPException(status_code=400, detail="Simülasyon zaten çalışıyor.")
        
    active_simulations[current_user.id] = True
    background_tasks.add_task(simulate_steps_task, current_user.id)
    return {"message": "Simülasyon başlatıldı. Her 5 saniyede bir 100 adım eklenecek."}


@router.post("/simulate/steps/stop")
async def stop_step_simulation(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Arka planda çalışan adım simülasyonunu durdurur. (Task 3.5)
    """
    if not active_simulations.get(current_user.id, False):
        raise HTTPException(status_code=400, detail="Çalışan bir simülasyon bulunamadı.")
        
    active_simulations[current_user.id] = False
    return {"message": "Simülasyon başarıyla durduruldu."}
