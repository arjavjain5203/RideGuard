"""Celery application setup and enqueue helpers."""

from __future__ import annotations

import logging
from typing import Any

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "rideguard",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=False,
    task_store_eager_result=True,
    result_expires=settings.CELERY_TASK_RESULT_EXPIRES,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT_SECONDS,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT_SECONDS,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)


def enqueue_task(task, *args: Any, **kwargs: Any):
    try:
        return task.apply_async(args=args, kwargs=kwargs)
    except Exception as exc:
        logger.exception("failed to enqueue celery task", extra={"task_name": getattr(task, "name", repr(task))})
        raise RuntimeError(f"Task queue unavailable: {exc}") from exc
