# Procfile for Modular Architecture (v2.0)
# API Service (Reads from Redis)
web: gunicorn api:app --workers 2 --worker-class gthread --threads 4 --timeout 60 --access-logfile - --bind 0.0.0.0:$PORT

# Worker Service (Telethon + Parser logic)
worker: python worker.py
