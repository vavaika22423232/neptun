# Procfile for Modular Architecture (v2.0)
# API Service (Reads from Redis)
web: gunicorn app_legacy:app --workers 1 --worker-class gevent --worker-connections 1000 --timeout 120 --keep-alive 5 --access-logfile - --bind 0.0.0.0:$PORT

# Worker Service (Telethon + Parser logic)
worker: python worker.py
