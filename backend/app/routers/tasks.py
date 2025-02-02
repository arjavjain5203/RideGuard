from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.core.celery_app import celery_app
from app.core.redis_client import get_cached_task_result
from app.models import User
from app.schemas import TaskStatusResponse

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    result = AsyncResult(task_id, app=celery_app)
    cached = get_cached_task_result(task_id) or {}
    payload = result.result if isinstance(result.result, dict) else cached or None

    error = None
    if result.failed():
        error = str(result.result)
    elif isinstance(payload, dict):
        error = payload.get("error")

    return TaskStatusResponse(
        task_id=task_id,
        status=(result.status or "PENDING").lower(),
        result_summary=payload if isinstance(payload, dict) else None,
        entity_id=(payload or {}).get("entity_id") if isinstance(payload, dict) else None,
        error=error,
    )
