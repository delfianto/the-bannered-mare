"""Admin API endpoints for log querying and system management"""

from datetime import datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query

from src.core.logging import mongo_logger

router = APIRouter(prefix="/admin/logs", tags=["admin", "logs"])


@router.get("/http")
async def query_http_logs(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(ge=0)] = 0,
    method: Annotated[str | None, Query()] = None,
    path: Annotated[str | None, Query()] = None,
    status_code: Annotated[int | None, Query()] = None,
    request_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Query HTTP request logs"""
    if not mongo_logger.initialized or mongo_logger.db is None:
        raise HTTPException(status_code=503, detail="MongoDB logging not initialized")

    # Build query filter
    filters = {}
    if method:
        filters["method"] = method
    if path:
        filters["path"] = {"$regex": path, "$options": "i"}
    if status_code:
        filters["status_code"] = status_code
    if request_id:
        filters["request_id"] = request_id

    # Query logs
    cursor = (
        cast(Any, mongo_logger.db)["http_logs"]
        .find(filters)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )

    logs: list[dict[str, Any]] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        logs.append(doc)

    # Get total count
    total = await cast(Any, mongo_logger.db)["http_logs"].count_documents(filters)

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip,
    }


@router.get("/llm")
async def query_llm_logs(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(ge=0)] = 0,
    chat_id: Annotated[str | None, Query()] = None,
    provider: Annotated[str | None, Query()] = None,
    model: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Query LLM API call logs"""
    if not mongo_logger.initialized or mongo_logger.db is None:
        raise HTTPException(status_code=503, detail="MongoDB logging not initialized")

    # Build query filter
    filters = {}
    if chat_id:
        filters["chat_id"] = chat_id
    if provider:
        filters["provider"] = provider
    if model:
        filters["model"] = {"$regex": model, "$options": "i"}
    if status:
        filters["status"] = status

    # Query logs
    cursor = (
        cast(Any, mongo_logger.db)["llm_audit"]
        .find(filters)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )

    logs: list[dict[str, Any]] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        logs.append(doc)

    # Get total count
    total = await cast(Any, mongo_logger.db)["llm_audit"].count_documents(filters)

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip,
    }


@router.get("/llm/stats")
async def get_llm_stats(
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    """Get aggregated LLM usage statistics"""
    if not mongo_logger.initialized or mongo_logger.db is None:
        raise HTTPException(status_code=503, detail="MongoDB logging not initialized")

    # Build match filter
    match_filter: dict[str, Any] = {}
    if start_date or end_date:
        match_filter["timestamp"] = {}
        if start_date:
            match_filter["timestamp"]["$gte"] = start_date
        if end_date:
            match_filter["timestamp"]["$lte"] = end_date

    # Aggregation pipeline
    pipeline: list[dict[str, Any]] = []
    if match_filter:
        pipeline.append({"$match": match_filter})

    pipeline.extend(
        [
            {
                "$group": {
                    "_id": {
                        "provider": "$provider",
                        "model": "$model",
                    },
                    "total_calls": {"$sum": 1},
                    "total_prompt_tokens": {"$sum": "$prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$completion_tokens"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_cost_usd": {"$sum": "$estimated_cost_usd"},
                    "avg_latency_ms": {"$avg": "$latency_ms"},
                    "success_count": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
                    "error_count": {"$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "provider": "$_id.provider",
                    "model": "$_id.model",
                    "total_calls": 1,
                    "total_prompt_tokens": 1,
                    "total_completion_tokens": 1,
                    "total_tokens": 1,
                    "total_cost_usd": {"$round": ["$total_cost_usd", 4]},
                    "avg_latency_ms": {"$round": ["$avg_latency_ms", 2]},
                    "success_count": 1,
                    "error_count": 1,
                    "success_rate": {
                        "$round": [
                            {
                                "$multiply": [
                                    {"$divide": ["$success_count", "$total_calls"]},
                                    100,
                                ]
                            },
                            2,
                        ]
                    },
                }
            },
            {"$sort": {"total_tokens": -1}},
        ]
    )

    stats: list[dict[str, Any]] = []
    cursor = await cast(Any, mongo_logger.db)["llm_audit"].aggregate(pipeline)
    async for doc in cursor:
        stats.append(doc)

    return {
        "stats": stats,
        "period": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
    }


@router.get("/errors")
async def query_error_logs(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(ge=0)] = 0,
    error_type: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Query application error logs"""
    if not mongo_logger.initialized or mongo_logger.db is None:
        raise HTTPException(status_code=503, detail="MongoDB logging not initialized")

    # Build query filter
    filters = {}
    if error_type:
        filters["error_type"] = error_type

    # Query logs
    cursor = (
        cast(Any, mongo_logger.db)["error_logs"]
        .find(filters)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )

    logs: list[dict[str, Any]] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        logs.append(doc)

    # Get total count
    total = await cast(Any, mongo_logger.db)["error_logs"].count_documents(filters)

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip,
    }
