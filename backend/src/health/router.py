"""Health check API endpoint"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.core.persistence import DbSession
from src.health.service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_health_service(db: DbSession) -> HealthService:
    return HealthService(db)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


@router.get("", status_code=status.HTTP_200_OK)
def get_health_status(service: HealthServiceDep):
    """Get application health status"""
    db_ok = service.get_db_status()
    storage_ok = service.get_storage_status()

    is_healthy = db_ok and storage_ok

    content = {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": "ok" if db_ok else "error",
        "storage": "ok" if storage_ok else "error",
    }

    if is_healthy:
        return content
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content,
        )
