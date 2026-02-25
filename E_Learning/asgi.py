"""
ASGI config for E_Learning project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_Learning.settings')

application = get_asgi_application()
