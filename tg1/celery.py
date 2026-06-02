import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tg1.settings")

app = Celery("tg1")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
