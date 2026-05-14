import random
from datetime import timedelta, datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()

# In-memory OTP deposu: phone_number -> {"code": "123456", "expires_at": datetime}
# Not: Prodüksiyonda bu işlem Redis üzerinde yapılmalıdır.
otp_store: Dict[str, Dict[str, Any]] = {}

class OTPRequest(BaseModel):
    phone_number: str = Field(..., description="Telefon numarası (Örn: +905551234567)")

class OTPVerify(BaseModel):
    phone_number: str = Field(..., description="Telefon numarası")
    otp_code: str = Field(..., description="SMS ile gelen 6 haneli kod")

@router.post("/request-otp")
async def request_otp(payload: OTPRequest) -> Any:
    """
    Telefon numarasına OTP kodu gönderir.
    Android geliştiricinin testi için üretilen kod terminale (konsola) basılır.
    """
    # 6 haneli rastgele bir OTP üret
    otp_code = str(random.randint(100000, 999999))
    
    # 3 dakika geçerlilik süresi
    expiration_time = datetime.utcnow() + timedelta(minutes=3)
    
    otp_store[payload.phone_number] = {
        "code": otp_code,
        "expires_at": expiration_time
    }
    
    # SMS API simülasyonu: Konsola yazdırıyoruz ki Android geliştirici loglardan görebilsin
    print("\n" + "="*50)
    print(f"📱 SMS GÖNDERİLDİ!")
    print(f"📍 Telefon: {payload.phone_number}")
    print(f"🔑 OTP Kodu: {otp_code}")
    print("="*50 + "\n")
    
    return {"message": "OTP kodu başarıyla gönderildi", "expires_in_minutes": 3}


@router.post("/login/otp", response_model=Token)
async def login_access_token_otp(
    payload: OTPVerify,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OTP kodu ile giriş yapar veya yeni kullanıcı kaydeder (Otomatik Kayıt).
    """
    stored_data = otp_store.get(payload.phone_number)
    
    if not stored_data:
        raise HTTPException(
            status_code=400, 
            detail="Bu telefon numarası için geçerli bir OTP bulunamadı veya süresi dolmuş."
        )
        
    if datetime.utcnow() > stored_data["expires_at"]:
        del otp_store[payload.phone_number]
        raise HTTPException(
            status_code=400, 
            detail="OTP kodunun süresi dolmuş. Lütfen yeni bir kod isteyin."
        )
        
    if stored_data["code"] != payload.otp_code:
        raise HTTPException(
            status_code=400, 
            detail="Hatalı OTP kodu."
        )
        
    # Doğrulama başarılı, güvenlik için OTP'yi bellekten sil
    del otp_store[payload.phone_number]
    
    # Kullanıcıyı bul veya oluştur
    result = await db.execute(select(User).where(User.phone_number == payload.phone_number))
    user = result.scalars().first()
    
    if not user:
        # Otomatik Kayıt
        user = User(
            phone_number=payload.phone_number,
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
    Swagger arabirimi (Authorize butonu) için OAuth2 login endpoint'i.
    Geliştirme aşamasında kolaylık için Swagger üzerinden test ederken şifre olarak '1234' kullanılabilir.
    """
    result = await db.execute(select(User).where(User.phone_number == form_data.username))
    user = result.scalars().first()
    
    if not user or form_data.password != "1234":
        raise HTTPException(status_code=400, detail="Incorrect username or password (use 1234 for Swagger)")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, role=user.role.value, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
