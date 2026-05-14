from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="SaglikCell CodeNight Backend API",
)

# Core API router inclusion
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to SaglikCell API",
        "docs_url": "/docs"
    }
