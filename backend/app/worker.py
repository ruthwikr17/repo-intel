from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "repoinsight",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.analysis_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=False,
    result_backend_transport_options={"retry_on_timeout": True},
)
