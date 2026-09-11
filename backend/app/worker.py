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
        "ssl_cert_reqs": "CERT_NONE",
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
    worker_prefetch_multiplier=1,
    task_always_eager=False,
    result_backend_transport_options={"retry_on_timeout": True},
    # Redis SSL options for Upstash
    broker_use_ssl=redis_ssl_config if redis_ssl_config else None,
    redis_backend_use_ssl=redis_ssl_config if redis_ssl_config else None,
)
