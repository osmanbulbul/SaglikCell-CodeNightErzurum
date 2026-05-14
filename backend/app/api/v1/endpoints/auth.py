from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()

@router.post("/login/otp", response_model=Token)
async def login_access_token_otp(
    phone_number: str,
    otp_code: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OTP ile giriş yapma simülasyonu.
    Geliştirme için geçerli OTP kodu: 1234
    """
    if otp_code != "1234":
        raise HTTPException(status_code=400, detail="Invalid OTP code")
        
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    user = result.scalars().first()
    
    if not user:
        # Otomatik Kayıt Simülasyonu
        user = User(
            phone_number=phone_number,
            password_hash=security.get_password_hash("default_password_for_otp")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, role=user.role.value, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Swagger arabirimi için OAuth2 login endpoint'i. username kısmına telefon numarası, password'a 1234 girilir.
    """
    result = await db.execute(select(User).where(User.phone_number == form_data.username))
    user = result.scalars().first()
    
    if not user or form_data.password != "1234":
        raise HTTPException(status_code=400, detail="Incorrect username or password (use 1234)")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, role=user.role.value, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
