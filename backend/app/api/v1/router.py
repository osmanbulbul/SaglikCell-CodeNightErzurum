from fastapi import APIRouter

api_router = APIRouter()

from app.api.v1.endpoints import auth, users, payments, metrics

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(payments.router, prefix="/payment", tags=["payment"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "message": "API is up and running"}
