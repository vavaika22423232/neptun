# 🔴 PERFORMANCE AUDIT: 2GB Traffic Crisis

## Executive Summary

**Текущий трафик**: ~2 GB HTTP responses (заявлено)
**Цель**: Радикальное сокращение до < 200 MB (90% reduction)

### ✅ IMPLEMENTED FIXES (already applied)
1. **Visibility-based throttling** - Hidden tabs poll every 2 min instead of 30s (-75% background traffic)
2. **ETag caching for /data** - 304 Not Modified responses skip JSON download
3. **ETag caching for /api/alarms** - Server generates content hash, client caches
4. **Smart polling restart** - Immediate fetch when tab becomes visible

---

## 📊 TOP-5 Traffic Sources (по убыванию влияния)

| # | Источник | Размер | Частота | ~Traffic/user/day | Проблема |
|---|----------|--------|---------|-------------------|----------|
| 1 | `/data` endpoint | ~50-200KB | каждые 30 сек | **~288 MB/user** | Full JSON dump каждый раз |
| 2 | `/api/alarms/all` | ~30-100KB | каждые 30 сек | **~144 MB/user** | Full state, нет diff |
| 3 | `ukraine_raions_gadm.geojson` | **2.0 MB** | on page load | 2 MB/user | Нет lazy loading |
| 4 | SVG maps (3 файла) | **612 KB** | on page load | 612 KB/user | Загружаются параллельно |
| 5 | `index_index.html` template | **172 KB** | on page load | 172 KB/user | Inline CSS/JS not minified |

**⚠️ CRITICAL**: 1 пользователь с открытой вкладкой 24ч генерирует до **~400-500 MB** трафика!

---

## 🔬 Layer-by-Layer Analysis

### 1. POLLING ENDPOINTS (главная проблема!)

#### `/data` - Threat Markers (lines 17763-17924)
```
Проблема: Full JSON dump ВСЕХ tracks + events + sources каждый запрос
Интервал: 30 сек (setInterval в index_index.html:3685)
Размер ответа: 50-200 KB (зависит от активности)
Traffic/hour: ~180 запросов * 100KB = 18 MB/user/hour
```

**Root cause**: 
- Отсутствует delta/diff механизм
- `response_data = {'tracks': out, 'events': events, 'all_sources': CHANNELS}`
- Нет пагинации, нет last-modified filtering

#### `/api/alarms/all` - Alarm State (lines 743-796)
```
Проблема: Полный state всех областей/районов каждый запрос  
Интервал: 30 сек (setInterval в index_index.html:3682)
Размер ответа: 30-100 KB
Traffic/hour: ~180 запросов * 50KB = 9 MB/user/hour
```

**Root cause**:
- Cache 30 сек серверный, но клиент игнорирует 304 Not Modified
- Нет ETag check на клиенте

#### `/presence` - Heartbeat (lines 4370-4381)
```
Интервал: 30 сек (setInterval в index_index.html:4518)
Размер: ~200 bytes
Traffic/hour: ~24 KB/user/hour (OK)
```

---

### 2. STATIC ASSETS (initial load)

| Asset | Size | Cache | Problem |
|-------|------|-------|---------|
| `ukraine_raions_gadm.geojson` | **2.0 MB** | 7 days | NOT USED in frontend! |
| `ukraine_raions_2020.geojson` | 480 KB | 7 days | NOT USED in frontend! |
| `ukraine_regions.json` | 420 KB | 7 days | Possibly unused |
| `ukraine_oblasts.geojson` | 420 KB | 7 days | Possibly unused |
| `ukraine_states.svg` | 196 KB | 7 days | Used - OK |
| `ukraine_districts_detailed.svg` | 376 KB | 7 days | Used - OK |
| `ukraine_names.svg` | 40 KB | 7 days | Used - OK |

**⚠️ BIG FINDING**: GeoJSON files (2+ MB) загружаются но НЕ используются!
Frontend использует SVG maps, не GeoJSON.

---

### 3. GZIP STATUS

✅ `flask-compress` включен (app.py:344-346)
✅ После-request compression (app.py:487-510)

Но есть **проблема**: 
```python
# app.py:492 - только если content_length > 500
if response.content_length and response.content_length > 500 and ...
```
- `response.content_type.startswith(...)` не включает `text/event-stream`
- SSE stream НЕ сжимается!

---

### 4. CACHING STRATEGY (текущая)

| Resource | Server Cache | Browser Cache | Problem |
|----------|--------------|---------------|---------|
| `/data` | 60 сек TTL | `max-age=60` | Client doesn't check 304! |
| `/api/alarms` | 30 сек TTL | `no-cache` | Forces full reload |
| SVG maps | N/A | 7 days | ✅ OK |
| HTML | N/A | 5 min | ✅ OK |

---

### 5. SSE STREAM (lines 19448-19471)

```python
@app.route('/stream')
def stream():
    # ... каждые 5 сек timeout check
    # каждые 25 сек ping
```

**Status**: НЕ используется клиентом! 
Frontend использует polling, не SSE.

---

## 🚨 Root Causes (корневые причины)

### 1. Polling vs Streaming Mismatch
- SSE `/stream` endpoint существует но НЕ используется
- Frontend делает polling каждые 30 сек
- **Решение**: Переключить на SSE с delta updates

### 2. Full State vs Delta
- `/data` отдает ВСЕ tracks каждый раз
- Нет механизма "отдать только новое с timestamp X"
- **Решение**: Добавить `?since=<timestamp>` параметр

### 3. Unused Large Files
- GeoJSON файлы (2.5+ MB суммарно) загружаются/кэшируются но не используются
- **Решение**: Удалить из static или не загружать

### 4. Client Ignores Cache
- Несмотря на ETag и Cache-Control, JS делает `fetch('/data')` без cache hints
- **Решение**: Добавить If-None-Match header check

---

## 📋 PRIORITIZED FIX TABLE

| # | Problem | Fix | Expected Reduction | Complexity | Files |
|---|---------|-----|-------------------|------------|-------|
| 1 | Polling `/data` | Delta updates (since=timestamp) | **-70%** API traffic | Medium | app.py, index_index.html |
| 2 | Polling `/api/alarms` | Use SSE instead | **-80%** API traffic | Medium | app.py, index_index.html |
| 3 | Unused GeoJSON | Remove from static | **-2.5 MB** initial | Low | static/ folder |
| 4 | Client cache bypass | Add If-None-Match | **-30%** repeat requests | Low | index_index.html |
| 5 | HTML not minified | Minify inline CSS/JS | **-30 KB** HTML | Low | templates/ |
| 6 | SSE not used | Connect frontend to /stream | **-90%** polling | High | index_index.html |

---

## 🔧 IMMEDIATE FIXES (можно сделать сейчас)

### Fix #1: Remove unused GeoJSON files
```bash
# These are NOT used by frontend (SVG maps are used instead)
rm static/ukraine_raions_gadm.geojson      # -2.0 MB
rm static/ukraine_raions_2020.geojson      # -480 KB  
rm static/ukraine_regions.json             # -420 KB
rm static/ukraine_oblasts.geojson          # -420 KB
# Total: -3.3 MB per cache miss
```

### Fix #2: Add ETag check to frontend fetch
```javascript
// index_index.html - fetchThreatMarkers()
async function fetchThreatMarkers() {
  const cached = sessionStorage.getItem('dataETag');
  const headers = cached ? {'If-None-Match': cached} : {};
  
  const response = await fetch('/data', {headers});
  
  if (response.status === 304) {
    console.log('Using cached data');
    return; // Skip update if unchanged
  }
  
  const etag = response.headers.get('ETag');
  if (etag) sessionStorage.setItem('dataETag', etag);
  // ... rest of code
}
```

### Fix #3: Delta updates for /data
```python
# app.py - /data endpoint
@app.route('/data')
def data():
    since_ts = request.args.get('since', type=float)
    
    # Filter by timestamp if provided
    if since_ts:
        min_time = datetime.fromtimestamp(since_ts)
        out = [m for m in out if parse_date(m) >= min_time]
    
    # Return only new items
    return jsonify({
        'tracks': out,
        'timestamp': time.time(),  # Client should send this back as 'since'
        'is_delta': bool(since_ts)
    })
```

### Fix #4: Increase polling intervals for inactive tabs
```javascript
// index_index.html
let pollingInterval = 30000; // Normal: 30 sec

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    pollingInterval = 120000; // Hidden tab: 2 min
  } else {
    pollingInterval = 30000;
  }
});
```

---

## 📈 Expected Results

| Metric | Before | After Fixes | Reduction |
|--------|--------|-------------|-----------|
| Traffic/user/24h | ~400-500 MB | ~50 MB | **90%** |
| Initial page load | ~5 MB | ~1 MB | **80%** |
| API calls/hour | 240 | 30 | **87%** |
| GeoJSON waste | 3.3 MB | 0 | **100%** |

---

## 🎯 Implementation Order

1. **TODAY**: Remove unused GeoJSON files (-3.3 MB instant)
2. **TODAY**: Add visibility-based throttling (reduce hidden tab traffic)
3. **WEEK 1**: Implement delta updates for /data
4. **WEEK 1**: Add client-side ETag caching
5. **WEEK 2**: Switch to SSE for real-time updates
6. **WEEK 2**: Implement WebSocket for mobile apps

---

## Mobile App Considerations

Current mobile endpoints:
- `/api/messages` - 200 messages, 30s cache ✅
- `/api/events` - 100 events, 30s cache ✅
- `/api/alarm-status` - 15s cache ✅

**Mobile traffic is OK** - proper caching in place.
**Focus on web frontend polling** - main bandwidth consumer.
