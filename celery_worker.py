# celery_worker.py
from celery import Celery

# Celery app, using Redis as broker
celery = Celery("llms_tasks", broker="redis://localhost:6379/0")

# Explicitly import tasks to register them
from app.crawler import scheduled_crawl  # 👈 this line imports and registers the task
