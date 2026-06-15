from fastapi import APIRouter

from configs.settings import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "local_model": settings.local_model,
        "scheduler": "running",
    }