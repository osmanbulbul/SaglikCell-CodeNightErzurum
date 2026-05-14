from datetime import date, datetime, timezone
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api import deps
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.goal import Goal, GoalProgress, Streak
from app.models.badge import Badge, UserBadge
from app.schemas.goal import GoalCreate, GoalResponse, GoalProgressResponse, StreakResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Dahili Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

async def _update_streak(db: AsyncSession, user_id: UUID, streak_type: str) -> Streak:
    """
    Kullanıcının belirtilen türdeki streak'ini kontrol eder ve günceller.
    Eğer dün de aktifse streak artar, bugün zaten sayıldıysa dokunulmaz,
    birden fazla gün arandıysa streak sıfırlanır. (Task 4.3)
    """
    result = await db.execute(
        select(Streak).where(Streak.user_id == user_id, Streak.streak_type == streak_type)
    )
    streak = result.scalars().first()

    today = date.today()

    if not streak:
        streak = Streak(
            user_id=user_id,
            streak_type=streak_type,
            current_streak=1,
            longest_streak=1,
            last_activity_date=today
        )
        db.add(streak)
    else:
        if streak.last_activity_date == today:
            # Bugün zaten sayıldı, tekrar arttırma
            return streak

        diff = (today - streak.last_activity_date).days if streak.last_activity_date else 999

        if diff == 1:
            # Ardışık gün: streak devam ediyor
            streak.current_streak += 1
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        else:
            # Zincir kırıldı, sıfırla
            streak.current_streak = 1

        streak.last_activity_date = today

    return streak


async def check_badges(db: AsyncSession, user_id: UUID, context: dict) -> List[str]:
    """
    Belirli olaylar tetiklendiğinde uygun rozetleri kullanıcıya atar.
    context dict'i: {'total_steps': 12000, 'current_streak': 30, ...}
    Yeni kazanılan rozet isimlerini döndürür. (Task 4.4)
    """
    earned_names = []

    # Kazanılmış rozet id'lerini önceden çek (mükerrer eklemeyi önlemek için)
    existing_result = await db.execute(
        select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
    )
    existing_badge_ids = {row[0] for row in existing_result.all()}

    # Tüm rozet tanımlarını çek
    all_badges_result = await db.execute(select(Badge))
    all_badges: List[Badge] = all_badges_result.scalars().all()

    for badge in all_badges:
        if badge.id in existing_badge_ids:
            continue  # Zaten kazanılmış, atla

        # Kriter eşleştirme
        criteria = badge.criteria or ""

        should_award = False
        if criteria == "10K_STEPS" and context.get("total_steps", 0) >= 10000:
            should_award = True
        elif criteria == "30_DAY_STREAK" and context.get("current_streak", 0) >= 30:
            should_award = True
        elif criteria == "7_DAY_STREAK" and context.get("current_streak", 0) >= 7:
            should_award = True
        elif criteria == "FIRST_GOAL_COMPLETE" and context.get("goal_completed", False):
            should_award = True
        elif criteria == "5_GOALS_COMPLETE" and context.get("total_completed_goals", 0) >= 5:
            should_award = True

        if should_award:
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
            earned_names.append(badge.name)

    return earned_names


# ---------------------------------------------------------------------------
# CRUD Endpoint'leri (Task 4.1)
# ---------------------------------------------------------------------------

@router.post("/", response_model=GoalResponse)
async def create_goal(
    *,
    db: AsyncSession = Depends(get_db),
    goal_in: GoalCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Yeni bir hedef oluşturur.
    - Standart kullanıcılar en fazla 2 aktif hedef belirleyebilir (premium teklif tetiklenebilir).
    - Aynı tipten birden fazla aktif hedef olamaz.
    """
    # Premium kontrolü
    if current_user.role == UserRole.user:
        count_result = await db.execute(
            select(func.count(Goal.id))
            .where(Goal.user_id == current_user.id, Goal.is_active == True)
        )
        active_count = count_result.scalar() or 0
        if active_count >= 2:
            raise HTTPException(
                status_code=403,
                detail="Standart kullanıcılar en fazla 2 aktif hedef belirleyebilir. "
                       "Sınırsız hedef için Premium üyeliğe geçin."
            )

    # Aynı tipten aktif hedef var mı?
    dupe = await db.execute(
        select(Goal).where(
            Goal.user_id == current_user.id,
            Goal.goal_type == goal_in.goal_type,
            Goal.is_active == True
        )
    )
    if dupe.scalars().first():
        raise HTTPException(status_code=400, detail="Bu tipte zaten aktif bir hedefiniz var.")

    new_goal = Goal(
        user_id=current_user.id,
        goal_type=goal_in.goal_type,
        target_value=goal_in.target_value,
        expires_at=goal_in.expires_at,
    )
    db.add(new_goal)
    await db.commit()
    await db.refresh(new_goal)
    return new_goal


@router.get("/", response_model=List[GoalResponse])
async def list_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Kullanıcının aktif hedeflerini listeler."""
    result = await db.execute(
        select(Goal).where(Goal.user_id == current_user.id, Goal.is_active == True)
    )
    return list(result.scalars().all())


@router.delete("/{goal_id}")
async def deactivate_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Hedefi pasif duruma getirir (soft-delete)."""
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Hedef bulunamadı.")

    goal.is_active = False
    await db.commit()
    return {"message": "Hedef kaldırıldı."}


# ---------------------------------------------------------------------------
# İlerleme Güncelleme (Task 4.2)
# ---------------------------------------------------------------------------

@router.post("/{goal_id}/progress", response_model=GoalProgressResponse)
async def update_goal_progress(
    goal_id: UUID,
    current_value: float,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Hedef için günlük ilerleme yüzdesini hesaplar ve kaydeder.
    Hedef tamamlanırsa rozet kontrolünü tetikler. (Task 4.2 & 4.4)
    """
    goal_result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id, Goal.is_active == True)
    )
    goal = goal_result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Aktif hedef bulunamadı.")

    today = date.today()
    progress_result = await db.execute(
        select(GoalProgress).where(
            GoalProgress.goal_id == goal_id,
            GoalProgress.user_id == current_user.id,
            GoalProgress.date == today
        )
    )
    progress = progress_result.scalars().first()

    percentage = min(100.0, round((current_value / goal.target_value) * 100, 2))
    is_completed = percentage >= 100.0

    if not progress:
        progress = GoalProgress(
            goal_id=goal_id,
            user_id=current_user.id,
            date=today,
            current_value=current_value,
            progress_percentage=percentage,
            is_completed=is_completed,
        )
        db.add(progress)
    else:
        progress.current_value = current_value
        progress.progress_percentage = percentage
        progress.is_completed = is_completed

    newly_earned_badges = []

    if is_completed:
        # Streak güncelle (Task 4.3)
        streak = await _update_streak(db, current_user.id, f"goal_{goal.goal_type}")

        # Toplam tamamlanan hedef sayısını çek
        completed_count_result = await db.execute(
            select(func.count(GoalProgress.id)).where(
                GoalProgress.user_id == current_user.id,
                GoalProgress.is_completed == True
            )
        )
        total_completed = (completed_count_result.scalar() or 0) + 1  # Bu anlık eklenen dahil

        # Rozet kontrolü (Task 4.4)
        context = {
            "goal_completed": True,
            "total_completed_goals": total_completed,
            "current_streak": streak.current_streak,
        }
        newly_earned_badges = await check_badges(db, current_user.id, context)

    await db.commit()
    await db.refresh(progress)

    response_data = GoalProgressResponse.model_validate(progress)
    if newly_earned_badges:
        # Kazanılan rozetleri response'a not olarak ekle
        return {**response_data.model_dump(), "newly_earned_badges": newly_earned_badges}
    return response_data


@router.get("/{goal_id}/progress", response_model=List[GoalProgressResponse])
async def get_goal_progress_history(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Belirli bir hedefin haftalık/aylık ilerleme geçmişini döndürür. (Task 4.2)
    """
    result = await db.execute(
        select(GoalProgress)
        .where(GoalProgress.goal_id == goal_id, GoalProgress.user_id == current_user.id)
        .order_by(GoalProgress.date.desc())
        .limit(30)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Streak Sorgulama (Task 4.3)
# ---------------------------------------------------------------------------

@router.get("/streaks", response_model=List[StreakResponse])
async def get_streaks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Kullanıcının tüm streak (seri) kayıtlarını döndürür."""
    result = await db.execute(
        select(Streak).where(Streak.user_id == current_user.id)
    )
    return list(result.scalars().all())
