# Procfile для Render - HIGH LOAD OPTIMIZED

# Основний Flask додаток з gunicorn + gevent для високого навантаження
# - workers: кількість процесів (1 для free tier)
# - worker-class: gevent для асинхронної обробки тисяч запитів
# - worker-connections: максимум з'єднань на воркер (1000)
# - timeout: таймаут для запитів
# - keep-alive: час утримання з'єднань
web: gunicorn app:app --workers 1 --worker-class gevent --worker-connections 1000 --timeout 60 --keep-alive 5 --bind 0.0.0.0:$PORT

# Channel Forwarder Bot (опціонально, якщо потрібен окремий worker)
# worker: python channel_forwarder_render.py
