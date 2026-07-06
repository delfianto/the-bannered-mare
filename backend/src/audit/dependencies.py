"""Dependency injection factories for the audit module (read side)"""

from typing import Annotated

from fastapi import Depends

from src.audit.repository_async import AuditRepository
from src.audit.service import AuditQueryService
from src.core.persistence import AsyncDbSession


async def get_audit_repository(db: AsyncDbSession) -> AuditRepository:
    """Factory for AuditRepository with async DB injected"""
    return AuditRepository(db)


async def get_audit_query_service(
    repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AuditQueryService:
    """Factory for AuditQueryService"""
    return AuditQueryService(repo)


AuditQueryServiceDep = Annotated[AuditQueryService, Depends(get_audit_query_service)]
