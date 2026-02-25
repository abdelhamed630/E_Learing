"""
WSGI config for E_Learning project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_Learning.settings')

application = get_wsgi_application()
