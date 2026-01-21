# Procfile для Render
# Використовує app.py з повною логікою траєкторій

web: gunicorn app:app --workers 1 --worker-class gevent --worker-connections 1000 --timeout 120 --keep-alive 5 --bind 0.0.0.0:$PORT

# Channel Forwarder Bot (опціонально, якщо потрібен окремий worker)
# worker: python channel_forwarder_render.py
