from celery import Celery
from celery.schedules import crontab
from backend.app.core.config import settings

celery_app = Celery(
    "retail_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.app.tasks.batch_tasks",
        "backend.app.tasks.huff_tasks",
        "backend.app.tasks.report_tasks",
        "backend.app.tasks.demographics_tasks",
        "backend.app.tasks.poi_tasks",
        "backend.app.tasks.analysis_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Minsk",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "backend.app.tasks.batch_tasks.*": {"queue": "batch"},
        "backend.app.tasks.huff_tasks.*": {"queue": "analysis"},
        "backend.app.tasks.report_tasks.*": {"queue": "reports"},
        "demographics.*": {"queue": "analysis"},
        "poi.*": {"queue": "batch"},
        "analysis.*": {"queue": "analysis"},
    },
    beat_schedule={
        # Refresh all regional demographics on 1st of each month at 03:00 Minsk time
        "demographics-monthly-refresh": {
            "task": "demographics.refresh_all",
            "schedule": crontab(hour=3, minute=0, day_of_month=1),
        },
    },
)
