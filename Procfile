# Procfile для Render - MODULAR ARCHITECTURE
# Використовує app_new.py з модульною архітектурою

web: gunicorn app_new:app --workers 1 --worker-class gevent --worker-connections 1000 --timeout 120 --keep-alive 5 --bind 0.0.0.0:$PORT --access-logfile /dev/null

# Channel Forwarder Bot (опціонально, якщо потрібен окремий worker)
# worker: python channel_forwarder_render.py
