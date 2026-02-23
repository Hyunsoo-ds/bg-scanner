from celery import Celery
from app.config import settings

celery_app = Celery(
    "bg_scanner",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.subdomain_task", "app.workers.port_task", "app.workers.tech_task", "app.workers.crawler_task", "app.workers.nuclei_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_routes={
        "app.workers.subdomain_task.*": {"queue": "subdomain"},
        # 추후 다른 큐 추가
    },
)
