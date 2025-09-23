"""
إعداد Celery للمهام الخلفية
"""
import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('deepfake_detection')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat settings
app.conf.beat_schedule = {
    'cleanup-expired-uploads': {
        'task': 'detector.tasks.cleanup_expired_uploads',
        'schedule': 3600.0,  # كل ساعة
    },
    'cleanup-debug-files': {
        'task': 'detector.tasks.cleanup_debug_files',
        'schedule': 86400.0,  # كل يوم
    },
}

app.conf.timezone = 'Asia/Baghdad'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
