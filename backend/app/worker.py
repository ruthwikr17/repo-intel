from celery import Celery
from app.config import get_settings

settings = get_settings()

# Build broker and backend URLs with SSL config for Upstash
def get_redis_url_with_ssl(url: str) -> str:
    """Return URL as-is for redis://, add SSL params for rediss://"""
    if url.startswith("rediss://"):
        return url
    return url


# SSL config needed when using rediss:// (Upstash)
redis_ssl_config = {}
if settings.redis_url.startswith("rediss://"):
    redis_ssl_config = {
        "ssl_cert_reqs": "none",
    }

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
    # If a worker process is lost, return the unacknowledged job to Redis so a
    # replacement worker can process it instead of silently losing the work.
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_always_eager=False,
    # Keep trying while Render or Upstash is briefly unavailable during a
    # deploy/cold start.  Celery 6 requires the explicit startup option.
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    broker_connection_retry=True,
    broker_connection_timeout=10,
    redis_socket_connect_timeout=10,
    redis_socket_timeout=10,
    result_backend_transport_options={"retry_on_timeout": True},
    result_backend_always_retry=True,
    result_backend_max_retries=3,
    result_expires=60 * 60 * 24,
    # Redis SSL options for Upstash
    broker_use_ssl=redis_ssl_config if redis_ssl_config else None,
    redis_backend_use_ssl=redis_ssl_config if redis_ssl_config else None,
)
