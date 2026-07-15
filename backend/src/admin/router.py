"""Admin API endpoints for querying persisted audit logs"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from src.audit.dependencies import AuditQueryServiceDep
from src.audit.schemas import (
    ErrorLogResponse,
    HttpLogResponse,
    LlmAuditLogResponse,
    LlmStatsResponse,
)
from src.core.pagination import ADMIN_DEFAULT_PAGE_SIZE, ADMIN_MAX_PAGE_SIZE
from src.core.schemas import PaginatedResponse

router = APIRouter(prefix="/admin/logs", tags=["admin", "logs"])


@router.get("/http")
async def query_http_logs(
    service: AuditQueryServiceDep,
    limit: Annotated[int, Query(ge=1, le=ADMIN_MAX_PAGE_SIZE)] = ADMIN_DEFAULT_PAGE_SIZE,
    skip: Annotated[int, Query(ge=0)] = 0,
    method: Annotated[str | None, Query()] = None,
    path: Annotated[str | None, Query()] = None,
    status_code: Annotated[int | None, Query()] = None,
    request_id: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[HttpLogResponse]:
    """Query HTTP request logs"""
    return await service.query_http(
        limit=limit,
        skip=skip,
        method=method,
        path=path,
        status_code=status_code,
        request_id=request_id,
    )


@router.get("/llm")
async def query_llm_logs(
    service: AuditQueryServiceDep,
    limit: Annotated[int, Query(ge=1, le=ADMIN_MAX_PAGE_SIZE)] = ADMIN_DEFAULT_PAGE_SIZE,
    skip: Annotated[int, Query(ge=0)] = 0,
    chat_id: Annotated[str | None, Query()] = None,
    provider: Annotated[str | None, Query()] = None,
    model: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[LlmAuditLogResponse]:
    """Query LLM API call logs"""
    return await service.query_llm(
        limit=limit,
        skip=skip,
        chat_id=chat_id,
        provider=provider,
        model=model,
        status=status,
    )


@router.get("/llm/stats")
async def get_llm_stats(
    service: AuditQueryServiceDep,
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
) -> LlmStatsResponse:
    """Get aggregated LLM usage statistics"""
    return await service.llm_stats(start=start_date, end=end_date)


@router.get("/errors")
async def query_error_logs(
    service: AuditQueryServiceDep,
    limit: Annotated[int, Query(ge=1, le=ADMIN_MAX_PAGE_SIZE)] = ADMIN_DEFAULT_PAGE_SIZE,
    skip: Annotated[int, Query(ge=0)] = 0,
    error_type: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[ErrorLogResponse]:
    """Query application error logs"""
    return await service.query_errors(limit=limit, skip=skip, error_type=error_type)
