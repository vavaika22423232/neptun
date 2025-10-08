#!/usr/bin/env python3
"""
Тест системы мониторинга трафика
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from bandwidth_monitor import track_bandwidth, check_rate_limit, get_bandwidth_stats

class MockRequest:
    """Mock объект для имитации Flask request"""
    def __init__(self, remote_addr='127.0.0.1', path='/test'):
        self.remote_addr = remote_addr
        self.path = path
        self.headers = {}

class MockResponse:
    """Mock объект для имитации Flask response"""
    def __init__(self, content_length=1024):
        self.content_length = content_length
        self.data = b'x' * content_length

def test_bandwidth_monitoring():
    """Тест основных функций мониторинга"""
    print("🧪 Тестирование системы мониторинга трафика")
    print("-" * 50)
    
    # Тест 1: Трекинг базового запроса
    print("1️⃣ Тест трекинга запроса...")
    request_mock = MockRequest('192.168.1.100', '/data')
    response_mock = MockResponse(2048)  # 2KB ответ
    
    track_bandwidth(response_mock, request_mock)
    
    stats = get_bandwidth_stats()
    print(f"   📊 Отправлено байт: {stats['total_bytes_sent']}")
    print(f"   👥 Активных IP: {stats['active_ips']}")
    
    if stats['total_bytes_sent'] > 0:
        print("   ✅ Трекинг работает")
    else:
        print("   ❌ Трекинг не работает")
    
    # Тест 2: Rate limiting
    print("\n2️⃣ Тест rate limiting...")
    test_ip = '192.168.1.200'
    
    # Имитируем множество запросов
    for i in range(10):
        mock_req = MockRequest(test_ip, f'/test{i}')
        mock_resp = MockResponse(512)
        track_bandwidth(mock_resp, mock_req)
    
    allowed, count = check_rate_limit(test_ip, max_requests_per_hour=5)
    print(f"   📈 Запросов с IP {test_ip}: {count}")
    print(f"   🛡️  Разрешен доступ: {'Да' if allowed else 'Нет'}")
    
    if count == 10:
        print("   ✅ Rate limiting работает")
    else:
        print("   ❌ Rate limiting не работает")
    
    # Тест 3: Статистика
    print("\n3️⃣ Тест статистики...")
    final_stats = get_bandwidth_stats()
    print(f"   📊 Общий трафик: {final_stats['total_mb_sent']:.2f}MB")
    print(f"   👥 Всего IP: {final_stats['active_ips']}")
    
    if final_stats['top_consumers']:
        top = final_stats['top_consumers'][0]
        print(f"   🔥 Топ потребитель: {top['ip']} ({top['mb']:.2f}MB)")
        print("   ✅ Статистика работает")
    else:
        print("   ❌ Статистика не работает")
    
    print(f"\n🎉 Тестирование завершено!")
    print(f"💡 Система мониторинга готова к работе")

if __name__ == "__main__":
    test_bandwidth_monitoring()
