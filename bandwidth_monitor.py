# BANDWIDTH MONITORING SYSTEM
# Добавьте этот код в начало app.py после других импортов

import time
from collections import defaultdict, deque
from threading import Lock

# Импорт Flask request для работы с HTTP запросами
try:
    from flask import request
except ImportError:
    # Fallback если Flask не доступен (для тестирования)
    request = None

# Глобальные переменные для мониторинга трафика
BANDWIDTH_MONITOR = {
    'total_bytes_sent': 0,
    'requests_by_ip': defaultdict(deque),
    'hourly_stats': deque(maxlen=24),  # последние 24 часа
    'lock': Lock()
}

def track_bandwidth(response, request_obj=None, request_size=0):
    """Отслеживать использование трафика"""
    try:
        # Используем переданный request объект или глобальный Flask request
        req = request_obj or request
        if not req:
            return  # Нет доступа к request объекту
            
        # Получаем размер ответа
        response_size = 0
        if hasattr(response, 'content_length') and response.content_length:
            response_size = response.content_length
        elif hasattr(response, 'data'):
            response_size = len(response.data)
        
        total_size = request_size + response_size
        
        with BANDWIDTH_MONITOR['lock']:
            BANDWIDTH_MONITOR['total_bytes_sent'] += total_size
            
            # Получаем IP клиента
            client_ip = getattr(req, 'remote_addr', 'unknown') or 'unknown'
            if hasattr(req, 'headers') and req.headers.get('X-Forwarded-For'):
                client_ip = req.headers.get('X-Forwarded-For').split(',')[0].strip()
            
            # Записываем запрос с временной меткой
            current_time = time.time()
            request_path = getattr(req, 'path', 'unknown')
            
            BANDWIDTH_MONITOR['requests_by_ip'][client_ip].append({
                'timestamp': current_time,
                'bytes': total_size,
                'path': request_path
            })
            
            # Очищаем старые записи (старше 1 часа)
            cutoff_time = current_time - 3600
            for ip in list(BANDWIDTH_MONITOR['requests_by_ip'].keys()):
                requests = BANDWIDTH_MONITOR['requests_by_ip'][ip]
                while requests and requests[0]['timestamp'] < cutoff_time:
                    requests.popleft()
                if not requests:
                    del BANDWIDTH_MONITOR['requests_by_ip'][ip]
        
        # Предупреждение о больших ответах
        if total_size > 1024 * 1024:  # > 1MB
            print(f"⚠️ BANDWIDTH WARNING: Large response {total_size//1024}KB to {client_ip} for {request_path}")
            
    except Exception as e:
        print(f"Error tracking bandwidth: {e}")

def check_rate_limit(client_ip, max_requests_per_hour=300):
    """Проверить лимит запросов для IP"""
    try:
        with BANDWIDTH_MONITOR['lock']:
            requests = BANDWIDTH_MONITOR['requests_by_ip'].get(client_ip, deque())
            
            # Подсчитываем запросы за последний час
            current_time = time.time()
            cutoff_time = current_time - 3600
            
            recent_requests = [req for req in requests if req['timestamp'] > cutoff_time]
            
            if len(recent_requests) > max_requests_per_hour:
                return False, len(recent_requests)
            
            return True, len(recent_requests)
    except Exception:
        return True, 0

def get_bandwidth_stats():
    """Получить статистику использования трафика"""
    try:
        with BANDWIDTH_MONITOR['lock']:
            stats = {
                'total_bytes_sent': BANDWIDTH_MONITOR['total_bytes_sent'],
                'total_mb_sent': round(BANDWIDTH_MONITOR['total_bytes_sent'] / 1024 / 1024, 2),
                'active_ips': len(BANDWIDTH_MONITOR['requests_by_ip']),
                'top_consumers': []
            }
            
            # Топ потребителей трафика
            ip_totals = {}
            for ip, requests in BANDWIDTH_MONITOR['requests_by_ip'].items():
                total_bytes = sum(req['bytes'] for req in requests)
                ip_totals[ip] = total_bytes
            
            # Сортируем по убыванию
            sorted_ips = sorted(ip_totals.items(), key=lambda x: x[1], reverse=True)
            stats['top_consumers'] = [
                {'ip': ip, 'bytes': bytes_used, 'mb': round(bytes_used/1024/1024, 2)}
                for ip, bytes_used in sorted_ips[:10]
            ]
            
            return stats
    except Exception as e:
        return {'error': str(e)}
