# E_Learning/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# إعداد Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_Learning.settings')

app = Celery('E_Learning')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()