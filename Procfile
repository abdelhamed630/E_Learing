web: gunicorn E_Learning.wsgi --log-file -
worker: celery -A E_Learning worker --loglevel=info
beat: celery -A E_Learning beat --loglevel=info