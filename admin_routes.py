import json
import os
import time
import platform
from datetime import datetime

from flask import Response, jsonify, request

# ===========================================================================
# EMERGENCY DDOS PROTECTION - Global rate limiter (module-level state)
# ===========================================================================
_ddos_ip_counts = {}  # {ip: [timestamps]}
_ddos_blocked_ips = set()  # Temporarily blocked IPs
_ddos_block_time = {}  # {ip: block_until_timestamp}
_ddos_last_cleanup = 0  # Last cleanup timestamp
DDOS_RATE_LIMIT = 50  # Max requests per IP per 10 seconds (raised - Cloudflare handles DDoS now)
DDOS_BLOCK_DURATION = 60  # Block IP for 60 seconds
DDOS_ENABLED = True  # Kill switch
DDOS_MAX_TRACKED_IPS = 300  # Max IPs to track before forced cleanup
DDOS_WHITELIST = set(os.environ.get('DDOS_WHITELIST', '').split(',')) - {''}

_INIT_BACKGROUND_DONE = False
INIT_ONCE = False

_FORCE_OVERRIDE = {'INIT_ONCE', '_INIT_BACKGROUND_DONE'}

def bind_dependencies(source_globals: dict):
    for name, value in source_globals.items():
        if name in _FORCE_OVERRIDE:
            globals()[name] = value
            continue
        if name not in globals():
            globals()[name] = value

def register_admin_routes(app):
    def _require_secret(req):
        if not AUTH_SECRET:
            return True
        supplied = req.args.get('secret') or req.headers.get('X-Auth-Secret') or req.form.get('secret')
        return supplied and supplied == AUTH_SECRET

    @app.route('/version')
    def version_check():
        return {'version': '2024-12-06-oblast-raion-fix', 'timestamp': time.time()}

    @app.route('/test_oblast_raion')
    def test_oblast_raion():
        if not _require_secret(request):
            return Response('Forbidden', status=403)

        test_text = "Загроза застосування БПЛА. Перейдіть в укриття! | чернігівська область (чернігівський район), київська область (вишгородський район), сумська область (сумський, конотопський райони) - загроза ударних бпла!"
        result = process_message(test_text, 'test_99999', '2024-12-06', 'test_channel')

        return {
            'test_text': test_text,
            'result': result,
            'debug_logs': [log for log in DEBUG_LOGS if log.get('category') == 'oblast_raion'][-10:]
        }

    @app.route('/test-pusk')
    def test_pusk_icon():
        """Test route to debug pusk.png display issues"""
        with open('/Users/vladimirmalik/Desktop/render2/test_pusk_icon.html', encoding='utf-8') as f:
            return f.read()

    @app.route('/clear_geocache')
    def clear_geocache():
        """Clear all geocoding caches (in-memory, file, and negative) to force re-geocoding"""
        global _mapstransler_geocode_cache
    
        # Clear in-memory cache
        old_count = len(_mapstransler_geocode_cache)
        _mapstransler_geocode_cache = {}
    
        # Clear OpenCage caches (both in-memory and file)
        try:
            import opencage_geocoder
            pos_count = len(opencage_geocoder._cache)
            neg_count = len(opencage_geocoder._negative_cache)
        
            # Clear in-memory
            opencage_geocoder._cache = {}
            opencage_geocoder._negative_cache = set()
        
            # Clear files
            opencage_geocoder._save_cache()
            opencage_geocoder._save_negative_cache()
        
            return f"Cleared {old_count} mapstransler + {pos_count} positive + {neg_count} negative cache entries. All cities will be re-geocoded."
        except Exception as e:
            return f"Cleared {old_count} mapstransler entries. OpenCage error: {e}"

    @app.route('/view_geocache')
    def view_geocache():
        """View current geocoding cache contents"""
        try:
            import opencage_geocoder
            cache_data = dict(opencage_geocoder._cache)
            neg_cache = list(opencage_geocoder._negative_cache)
            stats = opencage_geocoder.get_cache_stats()
            return jsonify({
                'positive_cache': {k: list(v) if isinstance(v, tuple) else v for k, v in cache_data.items()},
                'negative_cache': neg_cache,
                'stats': stats
            })
        except Exception as e:
            return jsonify({'error': str(e)})

    @app.route('/admin')
    def admin_panel():
        if not _require_secret(request):
            return Response('Forbidden', status=403)
        # Ensure rolling recent visits file is seeded from durable SQLite (survives redeploy)
        try:
            _seed_recent_from_sql()
        except Exception:
            pass
        now = time.time()
        # Merge ACTIVE_VISITORS volatile data with persistent DB to avoid session age resets on restart
        # Strategy: build dict from DB for active window; overlay runtime (for ip/ua freshness)
        db_active = {s['id']: s for s in _active_sessions_from_db(ACTIVE_TTL)}
        with ACTIVE_LOCK:
            visitors = []
            for vid, meta in ACTIVE_VISITORS.items():
                if isinstance(meta,(int,float)):
                    mem_first = meta
                    mem_last = meta
                    db_sess = db_active.get(vid)
                    if db_sess:
                        first_ts = db_sess.get('first') or mem_first
                        last_ts = db_sess.get('last') or mem_last
                    else:
                        first_ts = mem_first
                        last_ts = mem_last
                else:
                    mem_first = meta.get('first') or meta.get('ts', now)
                    mem_last = meta.get('ts', mem_first)
                    db_sess = db_active.get(vid)
                    if db_sess:
                        # Use earlier first (older session start) and later last (most recent activity)
                        first_ts = min(mem_first, db_sess.get('first') or mem_first)
                        last_ts = max(mem_last, db_sess.get('last') or mem_last)
                    else:
                        first_ts, last_ts = mem_first, mem_last
                if first_ts > last_ts:
                    first_ts, last_ts = last_ts, first_ts
                sess_age = int(now - first_ts)
                idle_age = int(now - last_ts)
                ua = (meta.get('ua') if isinstance(meta, dict) else '') or ''
                ip = (meta.get('ip') if isinstance(meta, dict) else '') or ''
                nickname = (meta.get('nickname') if isinstance(meta, dict) else '') or ''
                visitors.append({
                    'id': vid,
                    'ip': ip,
                    'age': sess_age,
                    'age_fmt': _fmt_age(sess_age),
                    'ua': ua,
                    'ua_short': _ua_label(ua) if ua else '',
                    'last_seen': _fmt_age(idle_age),
                    'nickname': nickname
                })
        blocked = load_blocked()
        # Load raw (pending geo) messages
        all_msgs = load_messages()
        raw_msgs = [m for m in reversed(all_msgs) if m.get('pending_geo')][:100]  # latest 100
        # Collect last N geo markers (exclude pending geo) for hide management
        recent_markers = [m for m in reversed(all_msgs) if m.get('lat') and m.get('lng') and not m.get('pending_geo')][:120]
        # --- Visit stats aggregation (prefer durable SQLite to survive redeploy) ---
        daily_unique, week_unique = sql_unique_counts()
        if daily_unique is None:
            # fallback to rolling sets file if DB unavailable
            daily_unique, week_unique = _recent_counts()
        if daily_unique is None:  # final fallback to json stats
            stats = _load_visit_stats()
            tz = pytz.timezone('Europe/Kyiv')
            now_dt = datetime.now(tz)
            today_str = now_dt.strftime('%Y-%m-%d')
            week_cut = now_dt - timedelta(days=7)
            daily_unique = 0
            week_unique = 0
            for vid, ts in stats.items():
                try:
                    tsf = float(ts)
                except Exception:
                    continue
                dt = datetime.fromtimestamp(tsf, tz)
                if dt.strftime('%Y-%m-%d') == today_str:
                    daily_unique += 1
                if dt >= week_cut:
                    week_unique += 1
        hidden_keys = load_hidden()
        parsed_hidden = []
        for hk in hidden_keys:
            try:
                coord_part, text_part, source_part = hk.split('|',2)
                lat_str, lng_str = coord_part.split(',',1)
                parsed_hidden.append({'lat':lat_str,'lng':lng_str,'text':text_part,'source':source_part,'key':hk})
            except Exception:
                continue

        # Load commercial subscriptions (from persistent storage)
        subscriptions = []
        if os.path.exists(COMMERCIAL_SUBSCRIPTIONS_FILE):
            try:
                with open(COMMERCIAL_SUBSCRIPTIONS_FILE, encoding='utf-8') as f:
                    subscriptions = json.load(f)
                # Sort by timestamp (newest first)
                subscriptions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            except Exception as e:
                print(f"❌ Failed to load subscriptions: {e}")

        return render_template(
            'admin.html',
            visitors=visitors,
            blocked=blocked,
            raw_msgs=raw_msgs,
            raw_count=len([m for m in all_msgs if m.get('pending_geo')]),
            secret=(request.args.get('secret') or ''),
            monitor_period=MONITOR_PERIOD_MINUTES,
            markers=recent_markers,
            daily_unique=daily_unique,
            week_unique=week_unique,
            hidden_markers=parsed_hidden,
            neg_geocode=list(_load_neg_geocode_cache().items())[:150],
            debug_logs=DEBUG_LOGS,
            redirect_stats=get_redirect_stats(),
            subscriptions=subscriptions
        )

    @app.route('/admin/clear_debug_logs', methods=['POST'])
    def clear_debug_logs():
        if not _require_secret(request):
            return jsonify({'status': 'forbidden'}), 403
        global DEBUG_LOGS
        DEBUG_LOGS.clear()
        return jsonify({'status': 'ok', 'cleared': True})

    @app.route('/admin/set_monitor_period', methods=['POST'])
    def set_monitor_period():
        if not _require_secret(request):
            return jsonify({'status': 'forbidden'}), 403
        global MONITOR_PERIOD_MINUTES
        payload = request.get_json(silent=True) or request.form
        try:
            val = int(payload.get('value'))
            if not (1 <= val <= 360):
                raise ValueError('out of range')
            MONITOR_PERIOD_MINUTES = val
            save_config()
            print(f"[DEBUG] MONITOR_PERIOD_MINUTES updated to {MONITOR_PERIOD_MINUTES} minutes")
            return jsonify({'status':'ok','monitor_period':MONITOR_PERIOD_MINUTES})
        except Exception as e:
            return jsonify({'status':'error','error':str(e)}), 400

    @app.route('/admin/toggle_ttl', methods=['POST'])
    def toggle_ttl_system():
        """Enable/disable TTL system for marker expiration"""
        if not _require_secret(request):
            return jsonify({'status': 'forbidden'}), 403
        global TTL_SYSTEM_ENABLED
        payload = request.get_json(silent=True) or request.form
        if payload and 'enabled' in payload:
            TTL_SYSTEM_ENABLED = str(payload.get('enabled')).lower() in ('true', '1', 'yes', 'on')
        else:
            TTL_SYSTEM_ENABLED = not TTL_SYSTEM_ENABLED  # Toggle if no value specified
        log.info(f"[TTL] System {'ENABLED' if TTL_SYSTEM_ENABLED else 'DISABLED'}")
        return jsonify({'status': 'ok', 'ttl_enabled': TTL_SYSTEM_ENABLED})

    @app.route('/admin/ttl_status', methods=['GET'])
    def get_ttl_status():
        """Get current TTL system status"""
        return jsonify({
            'ttl_enabled': TTL_SYSTEM_ENABLED,
            'max_ttl': 30,
            'rocket_ttl': 5,
            'shahed_ttl': 20,
            'ballistic_ttl': 4
        })

    @app.route('/admin/threat_tracker', methods=['GET'])
    def admin_threat_tracker():
        """Get current threat tracking status"""
        active_threats = THREAT_TRACKER.get_all_active_threats()

        # Serialize threats for JSON
        threats_json = []
        for t in active_threats:
            threat_copy = {}
            for k, v in t.items():
                if isinstance(v, datetime):
                    threat_copy[k] = v.isoformat()
                elif k == 'history':
                    # Skip history for summary
                    threat_copy[k] = len(v)
                else:
                    threat_copy[k] = v
            threats_json.append(threat_copy)

        # Summary by type
        by_type = {}
        for t in active_threats:
            tt = t.get('threat_type', 'unknown')
            if tt not in by_type:
                by_type[tt] = {'count': 0, 'total_quantity': 0, 'destroyed': 0}
            by_type[tt]['count'] += 1
            by_type[tt]['total_quantity'] += t.get('quantity', 1)
            by_type[tt]['destroyed'] += t.get('quantity_destroyed', 0)

        return jsonify({
            'active_threats': threats_json,
            'by_type': by_type,
            'total_active': len(active_threats),
            'total_tracked': len(THREAT_TRACKER.threats),
            'regions_with_threats': list(THREAT_TRACKER.region_to_threats.keys())
        })

    @app.route('/api/threats', methods=['GET'])
    def api_threats():
        """
        Public API for active threats - counts from recent messages.
        Used by mobile widget for real-time threat display.
        """
        try:
            from datetime import datetime, timedelta
            import pytz
            kyiv_tz = pytz.timezone('Europe/Kyiv')
            now_kyiv = datetime.now(kyiv_tz)
            cutoff_time = now_kyiv - timedelta(minutes=30)  # Only last 30 minutes
        
            messages = load_messages()
        
            # Count threats by type from recent messages
            drones = 0
            missiles = 0  
            kab = 0
            ballistic = 0
        
            seen_texts = set()  # Avoid counting duplicates
        
            for msg in messages[-200:]:  # Check last 200 messages
                if not isinstance(msg, dict):
                    continue
            
                text = (msg.get('text') or '').lower()
            
                # Check timestamp if available
                msg_date = msg.get('date') or msg.get('timestamp', '')
                if msg_date:
                    try:
                        if isinstance(msg_date, str):
                            # Parse various date formats
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                                try:
                                    dt = datetime.strptime(msg_date[:19], fmt)
                                    dt = kyiv_tz.localize(dt)
                                    break
                                except:
                                    continue
                            else:
                                continue
                        else:
                            continue
                    
                        if dt < cutoff_time:
                            continue
                    except:
                        pass
            
                # Normalize text for dedup
                text_key = text[:50]
                if text_key in seen_texts:
                    continue
                seen_texts.add(text_key)
            
                # Parse quantity if present (e.g. "2х БПЛА", "3 шахеди")
                qty = 1
                qty_match = re.search(r'(\d+)\s*[xхХ]?\s*(?:бпла|шахед|дрон|ракет|каб)', text)
                if qty_match:
                    qty = int(qty_match.group(1))
            
                # Count by type
                if any(w in text for w in ['шахед', 'shahed', 'герань']):
                    drones += qty
                elif any(w in text for w in ['бпла', 'дрон', 'uav', 'безпілот']):
                    drones += qty
                elif any(w in text for w in ['каб', 'керована бомба', 'авіабомб']):
                    kab += qty
                elif any(w in text for w in ['балістик', 'іскандер', 'ballistic']):
                    ballistic += qty
                elif any(w in text for w in ['крилат', 'калібр', 'х-101', 'cruise', 'ракет']):
                    missiles += qty
        
            # Build response with threat data
            threats = []
            if drones > 0:
                threats.append({
                    'threat_type': 'drone',
                    'quantity': drones,
                    'quantity_remaining': drones,
                    'status': 'active',
                    'created_at': now_kyiv.isoformat()
                })
            if missiles > 0:
                threats.append({
                    'threat_type': 'cruise',
                    'quantity': missiles,
                    'quantity_remaining': missiles,
                    'status': 'active',
                    'created_at': now_kyiv.isoformat()
                })
            if kab > 0:
                threats.append({
                    'threat_type': 'kab',
                    'quantity': kab,
                    'quantity_remaining': kab,
                    'status': 'active',
                    'created_at': now_kyiv.isoformat()
                })
            if ballistic > 0:
                threats.append({
                    'threat_type': 'ballistic',
                    'quantity': ballistic,
                    'quantity_remaining': ballistic,
                    'status': 'active',
                    'created_at': now_kyiv.isoformat()
                })
        
            return jsonify({
                'threats': threats,
                'summary': {
                    'total': drones + missiles + kab + ballistic,
                    'drones': drones,
                    'missiles': missiles,
                    'kab': kab,
                    'ballistic': ballistic
                },
                'updated_at': now_kyiv.isoformat()
            })
        
        except Exception as e:
            print(f"[API /api/threats] Error: {e}")
            return jsonify({
                'threats': [],
                'summary': {'total': 0, 'drones': 0, 'missiles': 0, 'kab': 0, 'ballistic': 0},
                'error': str(e)
            })

    @app.route('/api/fusion/events', methods=['GET'])
    def api_fusion_events():
        """
        API для отримання об'єднаних подій з системи злиття каналів.

        Повертає активні події з комбінованою інформацією з різних джерел.
        """
        try:
            events = CHANNEL_FUSION.get_active_events()

            # Group by status
            by_status = {
                'active': [],
                'partially_destroyed': [],
                'destroyed': [],
                'passed': [],
            }

            for event in events:
                status = event.get('status', 'active')
                if status in by_status:
                    by_status[status].append(event)
                else:
                    by_status['active'].append(event)

            # Serialize events
            serialized = []
            for event in events:
                ser_event = {
                    'id': event['id'],
                    'threat_type': event['threat_type'],
                    'quantity': event['quantity'],
                    'quantity_destroyed': event['quantity_destroyed'],
                    'regions': event['regions'],
                    'direction': event['direction'],
                    'status': event['status'],
                    'confidence': event['confidence'],
                    'coordinates': event['best_coordinates'],
                    'trajectory_points': len(event['trajectory']),
                    'source_count': len({m['channel'] for m in event['messages']}),
                    'sources': list({m['channel'] for m in event['messages']}),
                    'created_at': event['created_at'].isoformat(),
                    'last_update': event['last_update'].isoformat(),
                }
                serialized.append(ser_event)

            return jsonify({
                'status': 'ok',
                'events': serialized,
                'summary': {
                    'total': len(events),
                    'active': len(by_status['active']),
                    'destroyed': len(by_status['destroyed']),
                    'passed': len(by_status['passed']),
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/fusion/markers', methods=['GET'])
    def api_fusion_markers():
        """
        API для отримання маркерів з системи злиття.

        Ці маркери можна використовувати на карті замість звичайних.
        """
        try:
            markers = get_fused_markers()

            return jsonify({
                'status': 'ok',
                'markers': markers,
                'count': len(markers)
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/fusion/trajectories', methods=['GET'])
    def api_fusion_trajectories():
        """
        API для отримання траєкторій руху загроз.

        Повертає траєкторії побудовані з послідовних повідомлень.
        """
        try:
            trajectories = get_fused_trajectories()

            return jsonify({
                'status': 'ok',
                'trajectories': trajectories,
                'count': len(trajectories)
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/fusion/status', methods=['GET'])
    def api_fusion_status():
        """
        Статус системи злиття каналів.
        """
        try:
            with CHANNEL_FUSION.lock:
                total_events = len(CHANNEL_FUSION.fused_events)
                total_messages = len(CHANNEL_FUSION.message_to_event)

                # Count by channel
                channel_counts = {}
                ai_analyzed_count = 0
                for event in CHANNEL_FUSION.fused_events.values():
                    for msg in event['messages']:
                        ch = msg['channel']
                        channel_counts[ch] = channel_counts.get(ch, 0) + 1
                    # Check if AI analyzed
                    sig = event.get('signature', {})
                    if sig.get('ai_analyzed'):
                        ai_analyzed_count += 1

            return jsonify({
                'status': 'ok',
                'fusion_enabled': True,
                'ai_enabled': GROQ_ENABLED,
                'ai_model': GROQ_MODEL if GROQ_ENABLED else None,
                'ai_analyzed_events': ai_analyzed_count,
                'total_events': total_events,
                'total_messages_processed': total_messages,
                'by_channel': channel_counts,
                'channel_priorities': CHANNEL_FUSION.CHANNEL_PRIORITY,
                'mode': 'AI-FIRST' if GROQ_ENABLED else 'REGEX-FALLBACK',
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/admin/fusion/cleanup', methods=['POST'])
    def admin_fusion_cleanup():
        """
        Примусове очищення старих подій fusion.
        """
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403

        try:
            removed = CHANNEL_FUSION.cleanup_old_events(max_age_hours=1)
            return jsonify({
                'status': 'ok',
                'removed_events': removed
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/admin/neg_geocode_clear', methods=['POST'])
    def admin_neg_geocode_clear():
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
        global _neg_geocode_cache
        _neg_geocode_cache = {}
        _save_neg_geocode_cache()
        return jsonify({'status':'ok','cleared':True})

    @app.route('/admin/neg_geocode_delete', methods=['POST'])
    def admin_neg_geocode_delete():
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
        payload = request.get_json(silent=True) or {}
        name = (payload.get('name') or '').strip().lower()
        if not name:
            return jsonify({'status':'error','error':'name required'}),400
        cache = _load_neg_geocode_cache()
        if name in cache:
            del cache[name]
            _save_neg_geocode_cache()
            return jsonify({'status':'ok','deleted':True})
        return jsonify({'status':'error','error':'not found'}),404

    @app.route('/admin/geocode_cleanup', methods=['POST'])
    def admin_geocode_cleanup():
        """Clean up bad geocode cache entries (region center fallbacks with round coordinates)"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        try:
            result = cleanup_bad_cache_entries()
            return jsonify({
                'status': 'ok',
                'removed_count': result['removed_count'],
                'kept_count': result['kept_count'],
                'removed_entries': [{'key': k, 'coords': list(c)} for k, c in result['removed_entries'][:50]]
            })
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500

    @app.route('/admin/geocode_invalidate', methods=['POST'])
    def admin_geocode_invalidate():
        """Invalidate a specific geocode cache entry to force re-geocoding"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        payload = request.get_json(silent=True) or {}
        city = payload.get('city', '').strip()
        region = payload.get('region', '').strip() or None
    
        if not city:
            return jsonify({'status': 'error', 'error': 'city required'}), 400
    
        removed = invalidate_cache_entry(city, region)
        return jsonify({
            'status': 'ok',
            'invalidated': removed,
            'city': city,
            'region': region
        })

    @app.route('/admin/geocode_stats', methods=['GET'])
    def admin_geocode_stats():
        """Get OpenCage geocoder statistics"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        stats = get_cache_stats()
        return jsonify({
            'status': 'ok',
            'geocoder_available': GEOCODER_AVAILABLE,
            **stats
        })

    @app.route('/admin/memory', methods=['GET'])
    def admin_memory():
        """Memory usage endpoint - check what's using RAM"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        import gc
        gc.collect()
    
        def get_size(obj, seen=None):
            size = sys.getsizeof(obj)
            if seen is None:
                seen = set()
            obj_id = id(obj)
            if obj_id in seen:
                return 0
            seen.add(obj_id)
            if isinstance(obj, dict):
                size += sum([get_size(v, seen) for v in obj.values()])
                size += sum([get_size(k, seen) for k in obj.keys()])
            elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
                try:
                    size += sum([get_size(i, seen) for i in obj])
                except:
                    pass
            return size
    
        def fmt(size):
            for unit in ['B', 'KB', 'MB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} GB"
    
        caches = {
            'response_cache': (len(RESPONSE_CACHE._cache), get_size(RESPONSE_CACHE._cache)),
            'messages_cache': (1 if _MESSAGES_CACHE.get('data') else 0, get_size(_MESSAGES_CACHE)),
            'notifications_cache': (len(SENT_NOTIFICATIONS_CACHE), get_size(SENT_NOTIFICATIONS_CACHE)),
            'region_topic_cache': (len(_region_topic_cache), get_size(_region_topic_cache)),
            'threat_class_cache': (len(_threat_classification_cache), get_size(_threat_classification_cache)),
            'mapstransler_cache': (len(_mapstransler_geocode_cache), get_size(_mapstransler_geocode_cache)),
            'visitors': (len(ACTIVE_VISITORS), get_size(ACTIVE_VISITORS)),
            'debug_logs': (len(DEBUG_LOGS), get_size(DEBUG_LOGS)),
            'reparse_cache': (len(FALLBACK_REPARSE_CACHE), get_size(FALLBACK_REPARSE_CACHE)),
        }
    
        # Add Visicom cache stats if available
        try:
            from visicom_geocoder import _cache as visicom_cache, _negative_cache as visicom_neg_cache, get_stats as visicom_stats
            caches['visicom_cache'] = (len(visicom_cache), get_size(visicom_cache))
            caches['visicom_negative_cache'] = (len(visicom_neg_cache), get_size(visicom_neg_cache))
            result_visicom_stats = visicom_stats()
        except:
            result_visicom_stats = None
    
        total = sum(v[1] for v in caches.values())
    
        result = {'caches': {}, 'total': fmt(total)}
        for name, (count, size) in caches.items():
            result['caches'][name] = {'items': count, 'size': fmt(size)}
    
        # Add Visicom stats
        if result_visicom_stats:
            result['visicom'] = result_visicom_stats
    
        # Process memory if psutil available
        try:
            import psutil
            mem = psutil.Process().memory_info()
            result['process'] = {'rss': fmt(mem.rss), 'vms': fmt(mem.vms)}
        except:
            pass
    
        return jsonify(result)

    @app.route('/admin/clear_geocache', methods=['GET', 'POST'])
    def admin_clear_geocache():
        """Clear Visicom negative cache to retry failed geocoding."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        try:
            from visicom_geocoder import clear_negative_cache, _negative_cache, _cache
            old_neg = len(_negative_cache)
            clear_negative_cache()
            return jsonify({
                'status': 'ok',
                'cleared_negative': old_neg,
                'cache_size': len(_cache)
            })
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500

    @app.route('/admin/stats', methods=['GET'])
    def admin_stats():
        """Get comprehensive system statistics for admin dashboard"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403

        try:
            all_msgs = load_messages()
            now = time.time()
            pytz.timezone('Europe/Kyiv')

            # Message statistics
            total_messages = len(all_msgs)
            pending_geo = len([m for m in all_msgs if m.get('pending_geo')])
            with_coordinates = len([m for m in all_msgs if m.get('lat') and m.get('lng')])

            # Recent activity (last 24h)
            cutoff_24h = now - 86400
            recent_msgs = [m for m in all_msgs if _msg_timestamp(m) > cutoff_24h]

            # Threat type breakdown
            threat_counts = {}
            for msg in all_msgs:
                if not msg.get('pending_geo') and msg.get('lat') and msg.get('lng'):
                    threat_type = msg.get('threat_type', 'unknown')
                    threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1

            # System health
            with ACTIVE_LOCK:
                active_users = len(ACTIVE_VISITORS)
            blocked_users = len(load_blocked())
            hidden_markers = len(load_hidden())
            neg_cache_size = len(_load_neg_geocode_cache())
            debug_logs_count = len(DEBUG_LOGS)

            return jsonify({
                'status': 'ok',
                'stats': {
                    'messages': {
                        'total': total_messages,
                        'pending_geo': pending_geo,
                        'with_coordinates': with_coordinates,
                        'recent_24h': len(recent_msgs)
                    },
                    'threats': threat_counts,
                    'system': {
                        'active_users': active_users,
                        'blocked_users': blocked_users,
                        'hidden_markers': hidden_markers,
                        'neg_cache_size': neg_cache_size,
                        'debug_logs': debug_logs_count,
                        'monitor_period': MONITOR_PERIOD_MINUTES
                    },
                    'timestamp': now
                }
            })
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500

    # ==================== DDOS MONITORING ====================
    @app.route('/admin/ddos_status', methods=['GET'])
    def admin_ddos_status():
        """Get DDoS protection statistics."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        now = time.time()
    
        # Top IPs by request count
        top_ips = sorted(
            [(ip, len(ts)) for ip, ts in _ddos_ip_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:20]
    
        # Active blocks
        active_blocks = [
            {'ip': ip, 'until': _ddos_block_time.get(ip, 0), 'seconds_left': int(_ddos_block_time.get(ip, 0) - now)}
            for ip in _ddos_blocked_ips
            if _ddos_block_time.get(ip, 0) > now
        ]
    
        return jsonify({
            'enabled': DDOS_ENABLED,
            'rate_limit': DDOS_RATE_LIMIT,
            'block_duration': DDOS_BLOCK_DURATION,
            'tracked_ips': len(_ddos_ip_counts),
            'blocked_ips': len(_ddos_blocked_ips),
            'active_blocks': active_blocks,
            'top_ips': [{'ip': ip, 'requests_10s': count} for ip, count in top_ips]
        })

    @app.route('/admin/ddos_block', methods=['POST'])
    def admin_ddos_block():
        """Manually block an IP."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        payload = request.get_json(silent=True) or {}
        ip = payload.get('ip')
        duration = int(payload.get('duration', 3600))  # Default 1 hour
    
        if not ip:
            return jsonify({'status': 'error', 'error': 'ip required'}), 400
    
        _ddos_blocked_ips.add(ip)
        _ddos_block_time[ip] = time.time() + duration
        print(f"[DDOS] MANUAL BLOCK: {ip} for {duration}s")
    
        return jsonify({'status': 'ok', 'blocked': ip, 'duration': duration})

    @app.route('/admin/ddos_unblock', methods=['POST'])
    def admin_ddos_unblock():
        """Manually unblock an IP."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
    
        payload = request.get_json(silent=True) or {}
        ip = payload.get('ip')
    
        if not ip:
            return jsonify({'status': 'error', 'error': 'ip required'}), 400
    
        _ddos_blocked_ips.discard(ip)
        _ddos_block_time.pop(ip, None)
        print(f"[DDOS] MANUAL UNBLOCK: {ip}")
    
        return jsonify({'status': 'ok', 'unblocked': ip})

    # ==================== API PROTECTION MONITORING ====================
    @app.route('/admin/protection_status', methods=['GET'])
    def admin_protection_status():
        """Get API protection statistics for monitoring bandwidth/abuse."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403

        try:
            if API_PROTECTION_ENABLED:
                stats = get_protection_stats()
                return jsonify({
                    'status': 'ok',
                    'protection_enabled': True,
                    'max_response_size_mb': MAX_RESPONSE_SIZE_BYTES / 1024 / 1024,
                    'stats': stats,
                    'endpoint_limits': {
                        '/data': {'max_tracks': 200, 'max_events': 100},
                        '/api/messages': {'max_messages': 100},
                        '/api/events': {'max_process': 500, 'max_return': 100},
                        '/api/alarm-history': {'max_days': 7, 'max_results': 200},
                        '/alarms_stats': {'max_limit': 500, 'max_minutes': 360},
                    }
                })
            else:
                return jsonify({
                    'status': 'ok',
                    'protection_enabled': False,
                    'message': 'API protection module not loaded'
                })
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500
    # ===================================================================

    @app.route('/admin/cleanup', methods=['POST'])
    def admin_cleanup():
        """Clean up old data to maintain performance"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403

        payload = request.get_json(silent=True) or {}
        days_to_keep = int(payload.get('days', 7))  # Keep last 7 days by default

        try:
            cutoff_time = time.time() - (days_to_keep * 86400)

            # Clean old messages
            all_msgs = load_messages()
            old_count = len(all_msgs)
            new_msgs = [m for m in all_msgs if _msg_timestamp(m) > cutoff_time]

            # Always keep at least 100 most recent messages
            if len(new_msgs) < 100 and len(all_msgs) >= 100:
                new_msgs = sorted(all_msgs, key=_msg_timestamp, reverse=True)[:100]

            save_messages(new_msgs)

            # Clean old debug logs (keep last 500)
            global DEBUG_LOGS
            if len(DEBUG_LOGS) > 500:
                DEBUG_LOGS = DEBUG_LOGS[-500:]

            # Clean old visitor data from SQLite
            try:
                conn = sqlite3.connect(VISIT_DB_PATH)
                c = conn.cursor()
                c.execute("DELETE FROM visits WHERE first_seen < ?", (cutoff_time,))
                deleted_visits = c.rowcount
                conn.commit()
                conn.close()
            except Exception:
                deleted_visits = 0

            return jsonify({
                'status': 'ok',
                'cleaned': {
                    'messages': old_count - len(new_msgs),
                    'debug_logs': max(0, len(DEBUG_LOGS) - 500),
                    'visitor_records': deleted_visits
                },
                'remaining': {
                    'messages': len(new_msgs),
                    'debug_logs': len(DEBUG_LOGS)
                }
            })
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500

    @app.route('/admin/export', methods=['GET'])
    def admin_export():
        """Export data for backup/analysis"""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403

        export_type = request.args.get('type', 'messages')

        try:
            if export_type == 'messages':
                all_msgs = load_messages()
                # Remove sensitive data
                clean_msgs = []
                for msg in all_msgs:
                    clean_msg = {k: v for k, v in msg.items() if k not in ['id']}
                    clean_msgs.append(clean_msg)
                return jsonify({'status': 'ok', 'data': clean_msgs, 'count': len(clean_msgs)})

            elif export_type == 'stats':
                with ACTIVE_LOCK:
                    active_count = len(ACTIVE_VISITORS)

                return jsonify({
                    'status': 'ok',
                    'data': {
                        'active_users': active_count,
                        'blocked_users': len(load_blocked()),
                        'hidden_markers': len(load_hidden()),
                        'neg_cache_entries': len(_load_neg_geocode_cache()),
                        'debug_logs': len(DEBUG_LOGS),
                        'monitor_period': MONITOR_PERIOD_MINUTES,
                        'export_time': time.time()
                    }
                })

            else:
                return jsonify({'status': 'error', 'error': 'Invalid export type'}), 400

        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500
            _save_neg_geocode_cache()
            return jsonify({'status':'ok','removed':name})
        return jsonify({'status':'ok','removed':None})

    @app.route('/block', methods=['POST'])
    def block_id():
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
        payload = request.get_json(silent=True) or request.form
        vid = (payload or {}).get('id')
        if not vid:
            return jsonify({'status':'error','error':'id required'}), 400
        blocked = load_blocked()
        if vid not in blocked:
            blocked.append(vid)
            save_blocked(blocked)
        # push control event so client can self-block immediately
        broadcast_control({'type':'block','id':vid})
        return jsonify({'status':'ok','blocked':blocked})

    @app.route('/unblock', methods=['POST'])
    def unblock_id():
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
        payload = request.get_json(silent=True) or request.form
        vid = (payload or {}).get('id')
        if not vid:
            return jsonify({'status':'error','error':'id required'}), 400
        blocked = load_blocked()
        if vid in blocked:
            blocked.remove(vid)
            save_blocked(blocked)
        return jsonify({'status':'ok','blocked':blocked})

    @app.route('/admin/hidden_markers')
    def admin_hidden_markers():
        """Return list of all hidden markers with metadata."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
        hidden_keys = load_hidden()
        hidden_list = []
        for key in hidden_keys:
            try:
                parts = key.split('|', 2)
                if len(parts) >= 3:
                    lat_lng, text, source = parts
                    lat_str, lng_str = lat_lng.split(',')
                    hidden_list.append({
                        'lat': float(lat_str),
                        'lng': float(lng_str),
                        'text': text,
                        'source': source,
                        'key': key
                    })
            except Exception as e:
                log.warning(f"Failed to parse hidden marker key: {key}, error: {e}")
        return jsonify({'status':'ok', 'hidden': hidden_list, 'count': len(hidden_list)})

    @app.route('/admin/unhide_marker', methods=['POST'])
    def admin_unhide_marker():
        """Unhide a marker (alias for /unhide_marker with auth check)."""
        if not _require_secret(request):
            return jsonify({'status':'forbidden'}), 403
        return unhide_marker()

    def _fmt_age(age_seconds:int)->str:
        # Format seconds to H:MM:SS (or M:SS if <1h)
        if age_seconds < 3600:
            m, s = divmod(age_seconds, 60)
            return f"{m}:{s:02d}"
        h, rem = divmod(age_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"

    def _ua_label(ua:str)->str:
        u = ua.lower()
        # Simple detection heuristics
        if 'android' in u:
            if 'wv' in u or 'version/' in u:
                base = 'Android WebView'
            else:
                base = 'Android'
        elif 'iphone' in u or 'ipad' in u or 'ipod' in u:
            base = 'iOS'
        elif 'mac os x' in u and 'mobile' not in u:
            base = 'macOS'
        elif 'windows nt' in u:
            base = 'Windows'
        elif 'linux' in u:
            base = 'Linux'
        else:
            base = 'Other'
        # Browser
        browser = 'Browser'
        if 'chrome/' in u and 'edg/' not in u and 'opr/' not in u:
            browser = 'Chrome'
        elif 'edg/' in u:
            browser = 'Edge'
        elif 'firefox/' in u:
            browser = 'Firefox'
        elif 'safari/' in u and 'chrome/' not in u:
            browser = 'Safari'
        elif 'opr/' in u or 'opera' in u:
            browser = 'Opera'
        return f"{base} {browser}"

    # NOTE: _load_opencage_cache, _save_opencage_cache, SETTLEMENTS_* defined earlier in the file

    # --------------- Optional Git auto-commit settings ---------------
    GIT_AUTO_COMMIT = os.getenv('GIT_AUTO_COMMIT', '0') not in ('0','false','False','')
    GIT_REPO_SLUG = os.getenv('GIT_REPO_SLUG')  # e.g. 'vavaika22423232/neptun'
    GIT_SYNC_TOKEN = os.getenv('GIT_SYNC_TOKEN')  # GitHub PAT (classic or fine-grained) with repo write
    GIT_COMMIT_INTERVAL = int(os.getenv('GIT_COMMIT_INTERVAL', '60'))  # seconds between commits (reduced for chat)
    _last_git_commit = 0
    _git_pull_done = False  # Track if initial pull was done

    # Delay before first Telegram connect (helps избежать пересечения старого и нового инстанса при деплое)
    FETCH_START_DELAY = int(os.getenv('FETCH_START_DELAY', '0'))  # seconds

    def git_pull_on_startup():
        """Pull latest data from GitHub on startup to restore chat messages."""
        global _git_pull_done
        if _git_pull_done:
            return
        if not GIT_AUTO_COMMIT or not GIT_REPO_SLUG or not GIT_SYNC_TOKEN:
            log.info("Git sync not configured, skipping pull on startup")
            return
        if not os.path.isdir('.git'):
            log.warning("Not a git repo, skipping pull")
            return
        try:
            def run(cmd):
                return subprocess.run(cmd, shell=True, capture_output=True, text=True)

            run('git config user.email "bot@local"')
            run('git config user.name "Auto Sync Bot"')

            safe_remote = f'https://x-access-token:{GIT_SYNC_TOKEN}@github.com/{GIT_REPO_SLUG}.git'
            remotes = run('git remote -v').stdout
            if 'origin' not in remotes or GIT_REPO_SLUG not in remotes:
                run('git remote remove origin')
                run(f'git remote add origin "{safe_remote}"')

            # Stash any local changes, pull, then pop
            run('git stash')
            pull_result = run('git pull origin main --rebase')
            run('git stash pop')

            if pull_result.returncode == 0:
                log.info("Git pull on startup successful - chat messages restored")
                # Copy pulled files to persistent storage if using /data directory
                _copy_git_files_to_persistent_storage()
            else:
                log.warning(f"Git pull failed: {pull_result.stderr}")

            _git_pull_done = True
        except Exception as e:
            log.error(f"Git pull on startup error: {e}")


    def _copy_git_files_to_persistent_storage():
        """Copy files from git repo to persistent storage directory after pull."""
        import shutil
        persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
        if not os.path.isdir(persistent_dir):
            log.info(f"No persistent storage at {persistent_dir}, skipping copy")
            return

        # Files to copy from repo root to persistent storage
        files_to_copy = ['chat_messages.json', 'messages.json', 'devices.json']

        for filename in files_to_copy:
            src = filename  # In repo root
            dst = os.path.join(persistent_dir, filename)

            if os.path.exists(src):
                try:
                    # Only copy if source is newer or destination doesn't exist
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        log.info(f"Copied {src} to {dst}")
                    else:
                        # Compare file sizes - copy if source has more data
                        src_size = os.path.getsize(src)
                        dst_size = os.path.getsize(dst)
                        if src_size > dst_size:
                            shutil.copy2(src, dst)
                            log.info(f"Updated {dst} from git (src={src_size}b, dst={dst_size}b)")
                        else:
                            log.info(f"Keeping existing {dst} (src={src_size}b, dst={dst_size}b)")
                except Exception as e:
                    log.error(f"Error copying {src} to {dst}: {e}")

    def maybe_git_autocommit():
        """If enabled, commit & push updated messages.json back to GitHub.
        Requirements:
          - Set GIT_AUTO_COMMIT=1
          - Provide GIT_REPO_SLUG (owner/repo)
          - Provide GIT_SYNC_TOKEN (PAT with repo write)
        The container build must include git (Render base images do).
        Commits throttled by GIT_COMMIT_INTERVAL seconds.
        """
        global _last_git_commit
        if not GIT_AUTO_COMMIT or not GIT_REPO_SLUG or not GIT_SYNC_TOKEN:
            return
        now = time.time()
        if now - _last_git_commit < GIT_COMMIT_INTERVAL:
            return
        if not os.path.isdir('.git'):
            raise RuntimeError('Not a git repo')

        # Copy files from persistent storage to repo root before committing
        _copy_persistent_files_to_git_repo()

        # Configure user (once)
        def run(cmd):
            return subprocess.run(cmd, shell=True, capture_output=True, text=True)
        run('git config user.email "bot@local"')
        run('git config user.name "Auto Sync Bot"')
        # Set remote URL embedding token (avoid logging token!)
        safe_remote = f'https://x-access-token:{GIT_SYNC_TOKEN}@github.com/{GIT_REPO_SLUG}.git'
        # Do not print safe_remote (contains secret)
        # Update origin only if needed
        remotes = run('git remote -v').stdout
        if 'origin' not in remotes or GIT_REPO_SLUG not in remotes:
            run('git remote remove origin')
            run(f'git remote add origin "{safe_remote}"')
        # Stage & commit if there is a change (use repo root filenames, not /data paths)
        run('git add messages.json')
        run('git add chat_messages.json')
        run('git add devices.json')
        status = run('git status --porcelain').stdout
        if 'messages.json' not in status and 'chat_messages.json' not in status and 'devices.json' not in status:
            return  # no actual diff
        commit_msg = 'Update messages (auto)'  # no secrets
        run(f'git commit -m "{commit_msg}"')
        push_res = run('git push origin HEAD:main')
        if push_res.returncode == 0:
            _last_git_commit = now
            log.info("Git autocommit successful")
        else:
            # If push fails (e.g., diverged), attempt pull+rebase then push
            run('git fetch origin')
            run('git rebase origin/main || git rebase --abort')
            push_res2 = run('git push origin HEAD:main')
            if push_res2.returncode == 0:
                _last_git_commit = now
            # else: give up silently to avoid spamming logs


    def _copy_persistent_files_to_git_repo():
        """Copy files from persistent storage to repo root for git commit."""
        import shutil
        persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
        if not os.path.isdir(persistent_dir):
            return  # Not using persistent storage

        files_to_copy = ['chat_messages.json', 'messages.json', 'devices.json']

        for filename in files_to_copy:
            src = os.path.join(persistent_dir, filename)
            dst = filename  # Repo root

            if os.path.exists(src):
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    log.error(f"Error copying {src} to {dst} for git: {e}")

    # NOTE: _load_settlements() defined and called earlier in the file

    """(Removed duplicate legacy process_message; canonical version defined earlier.)"""

    # ----------------------- Deferred initialization hooks -----------------------
    # CPU OPTIMIZATION: Use before_first_request pattern manually

    def _memory_cleanup_worker():
        """Background worker to periodically clean up caches and prevent memory leaks."""
        cleanup_counter = 0
        while True:
            try:
                time.sleep(60)  # Run every 1 minute (more aggressive)
                cleanup_counter += 1
                now = time.time()
                total_cleaned = 0
            
                # Force garbage collection EVERY cycle
                import gc
                gc.collect()
            
                # Clean request_counts
                _cleanup_request_counts()
            
                # Clean ResponseCache expired entries
                cleaned = RESPONSE_CACHE.clear_expired()
                total_cleaned += cleaned
            
                # Clean _groq_cache - remove old entries and enforce size limit
                if _groq_cache:
                    old_size = len(_groq_cache)
                    expired_keys = [k for k, (_, ts) in _groq_cache.items() if now - ts > _groq_cache_ttl]
                    for k in expired_keys:
                        _groq_cache.pop(k, None)
                    # If still over limit, remove oldest entries
                    if len(_groq_cache) > _groq_cache_max_size:
                        sorted_keys = sorted(_groq_cache.keys(), key=lambda k: _groq_cache[k][1])
                        for k in sorted_keys[:len(_groq_cache) - _groq_cache_max_size // 2]:
                            _groq_cache.pop(k, None)
                    total_cleaned += old_size - len(_groq_cache)
            
                # Clean _telegram_alert_sent (keep only last 3 min)
                with _telegram_alert_lock:
                    keys_to_del = [k for k, v in _telegram_alert_sent.items() if now - v > 180]
                    for k in keys_to_del:
                        _telegram_alert_sent.pop(k, None)
                    total_cleaned += len(keys_to_del)
            
                # Clean _telegram_region_notified (keep only last 5 min)
                keys_to_del = [k for k, v in list(_telegram_region_notified.items()) if now - v > 300]
                for k in keys_to_del:
                    _telegram_region_notified.pop(k, None)
                total_cleaned += len(keys_to_del)
                
                # Clean ACTIVE_VISITORS (remove stale visitors - aggressive)
                with ACTIVE_LOCK:
                    old_size = len(ACTIVE_VISITORS)
                    stale_keys = [k for k, v in ACTIVE_VISITORS.items() if now - v.get('ts', 0) > ACTIVE_TTL]
                    for k in stale_keys:
                        ACTIVE_VISITORS.pop(k, None)
                    # Hard limit on active visitors
                    if len(ACTIVE_VISITORS) > 500:
                        # Remove oldest visitors
                        sorted_keys = sorted(ACTIVE_VISITORS.keys(), key=lambda k: ACTIVE_VISITORS[k].get('ts', 0))
                        for k in sorted_keys[:len(ACTIVE_VISITORS) - 300]:
                            ACTIVE_VISITORS.pop(k, None)
                    total_cleaned += old_size - len(ACTIVE_VISITORS)
            
                # Clean _mapstransler_geocode_cache if over limit
                if len(_mapstransler_geocode_cache) > _mapstransler_cache_max_size:
                    old_size = len(_mapstransler_geocode_cache)
                    keys_to_remove = list(_mapstransler_geocode_cache.keys())[:old_size // 2]
                    for k in keys_to_remove:
                        _mapstransler_geocode_cache.pop(k, None)
                    total_cleaned += old_size - len(_mapstransler_geocode_cache)
            
                # Clean _RF_GEOCODE_CACHE
                if len(_RF_GEOCODE_CACHE) > _RF_GEOCODE_CACHE_MAX:
                    sorted_keys = sorted(_RF_GEOCODE_CACHE.keys(), key=lambda k: _RF_GEOCODE_CACHE[k][1] if _RF_GEOCODE_CACHE[k] else 0)
                    for k in sorted_keys[:len(_RF_GEOCODE_CACHE) // 2]:
                        _RF_GEOCODE_CACHE.pop(k, None)
            
                # Clean _REGION_IDS_CACHE
                if len(_REGION_IDS_CACHE) > _REGION_IDS_CACHE_MAX:
                    sorted_keys = sorted(_REGION_IDS_CACHE.keys(), key=lambda k: _REGION_IDS_CACHE[k].get('ts', 0))
                    for k in sorted_keys[:len(_REGION_IDS_CACHE) // 2]:
                        _REGION_IDS_CACHE.pop(k, None)
            
                # Clean _OBLAST_ID_CACHE (limit to 100 entries)
                if len(_OBLAST_ID_CACHE) > 100:
                    keys_to_remove = list(_OBLAST_ID_CACHE.keys())[:len(_OBLAST_ID_CACHE) - 50]
                    for k in keys_to_remove:
                        _OBLAST_ID_CACHE.pop(k, None)
            
                # Clean SENT_NOTIFICATIONS_CACHE
                global SENT_NOTIFICATIONS_CACHE
                SENT_NOTIFICATIONS_CACHE = {
                    h: t for h, t in SENT_NOTIFICATIONS_CACHE.items()
                    if now - t < NOTIFICATION_CACHE_TTL
                }
            
                # CRITICAL: Clean _region_topic_cache (can grow unbounded)
                with _region_topic_cache_lock:
                    if len(_region_topic_cache) > 100:
                        keys_to_remove = list(_region_topic_cache.keys())[:len(_region_topic_cache) - 50]
                        for k in keys_to_remove:
                            _region_topic_cache.pop(k, None)
                        total_cleaned += len(keys_to_remove)
            
                # CRITICAL: Clean _ddos_ip_counts more aggressively
                if len(_ddos_ip_counts) > 100:
                    old_size = len(_ddos_ip_counts)
                    for ip in list(_ddos_ip_counts.keys()):
                        _ddos_ip_counts[ip] = [t for t in _ddos_ip_counts[ip] if now - t < 10]
                        if not _ddos_ip_counts[ip]:
                            del _ddos_ip_counts[ip]
                    total_cleaned += old_size - len(_ddos_ip_counts)
            
                # Clean _active_alarms_cache (can grow unbounded)
                if len(_active_alarms_cache) > 50:
                    keys_to_remove = list(_active_alarms_cache.keys())[:len(_active_alarms_cache) - 30]
                    for k in keys_to_remove:
                        _active_alarms_cache.pop(k, None)
                    total_cleaned += len(keys_to_remove)
            
                # Force garbage collection every cleanup
                gc.collect()
            
                # CRITICAL: Check memory and force aggressive cleanup if near limit
                try:
                    import psutil
                    process = psutil.Process()
                    mem_mb = process.memory_info().rss / 1024 / 1024
                
                    # If over 1.5GB, emergency cleanup
                    if mem_mb > 1500:
                        print(f"[MEMORY] EMERGENCY: {mem_mb:.0f}MB - forcing aggressive cleanup")
                    
                        # Clear all non-essential caches
                        RESPONSE_CACHE._cache.clear()
                        _mapstransler_geocode_cache.clear()
                        _RF_GEOCODE_CACHE.clear()
                        _REGION_IDS_CACHE.clear()
                        _OBLAST_ID_CACHE.clear()
                        _active_alarms_cache.clear()
                    
                        # Trim visitors to 200
                        with ACTIVE_LOCK:
                            if len(ACTIVE_VISITORS) > 200:
                                sorted_keys = sorted(ACTIVE_VISITORS.keys(), key=lambda k: ACTIVE_VISITORS[k].get('ts', 0))
                                for k in sorted_keys[:len(ACTIVE_VISITORS) - 200]:
                                    ACTIVE_VISITORS.pop(k, None)
                    
                        gc.collect()
                        gc.collect()  # Double collect
                    
                        new_mem = process.memory_info().rss / 1024 / 1024
                        print(f"[MEMORY] After emergency cleanup: {new_mem:.0f}MB (freed {mem_mb - new_mem:.0f}MB)")
                    
                except ImportError:
                    pass
            
                # Log memory status every 5 cleanups (5 min)
                if cleanup_counter % 5 == 0 and total_cleaned > 0:
                    try:
                        import psutil
                        process = psutil.Process()
                        mem_mb = process.memory_info().rss / 1024 / 1024
                        print(f"[MEMORY] Cleanup #{cleanup_counter}: cleaned {total_cleaned} items, using {mem_mb:.1f}MB")
                    except:
                        print(f"[MEMORY] Cleanup #{cleanup_counter}: cleaned {total_cleaned} items")
                    
            except Exception as e:
                print(f"[MEMORY] Cleanup worker error: {e}")

    def _init_background():
        global _INIT_BACKGROUND_DONE, INIT_ONCE
        if _INIT_BACKGROUND_DONE:
            return
        _INIT_BACKGROUND_DONE = True
        INIT_ONCE = True
        _startup_diagnostics()
        # Start background workers
        try:
            start_fetch_thread()
        except Exception as e:
            log.error(f'Failed to start fetch thread: {e}\n{traceback.format_exc()}')
        try:
            start_session_watcher()
        except Exception as e:
            log.error(f'Failed to start session watcher: {e}\n{traceback.format_exc()}')
        # MEMORY PROTECTION: Start memory cleanup worker
        try:
            threading.Thread(target=_memory_cleanup_worker, daemon=True, name='memory_cleanup').start()
            print("INFO: Memory cleanup worker started")
        except Exception as e:
            log.error(f'Failed to start memory cleanup worker: {e}')

    @app.before_request
    def _ddos_protection():
        """Emergency DDoS protection - block abusive IPs."""
        global _ddos_last_cleanup
        try:
            if not DDOS_ENABLED:
                return None

            # Skip for health checks, presence, and static files
            if request.path in ['/healthz', '/health', '/startup_diag', '/presence']:
                return None
            if request.path.startswith('/static/'):
                return None

            # Use Cloudflare-aware IP detection
            client_ip = get_real_ip()

            # Skip whitelisted IPs (admins)
            if client_ip in DDOS_WHITELIST:
                return None

            now = time.time()

            # Check if IP is blocked
            if client_ip in _ddos_blocked_ips:
                block_until = _ddos_block_time.get(client_ip, 0)
                if now < block_until:
                    return Response(
                        '{"error":"rate_limited","blocked":true}',
                        status=429,
                        mimetype='application/json'
                    )
                else:
                    # Unblock
                    _ddos_blocked_ips.discard(client_ip)
                    _ddos_block_time.pop(client_ip, None)

            # Count requests
            if client_ip not in _ddos_ip_counts:
                _ddos_ip_counts[client_ip] = []

            # Remove old timestamps (older than 10 seconds)
            _ddos_ip_counts[client_ip] = [t for t in _ddos_ip_counts[client_ip] if now - t < 10]
            _ddos_ip_counts[client_ip].append(now)

            # Check if exceeds limit
            if len(_ddos_ip_counts[client_ip]) > DDOS_RATE_LIMIT:
                _ddos_blocked_ips.add(client_ip)
                _ddos_block_time[client_ip] = now + DDOS_BLOCK_DURATION
                print(f"[DDOS] BLOCKED IP {client_ip} - {len(_ddos_ip_counts[client_ip])} requests in 10s")
                return Response(
                    '{"error":"rate_limited","blocked":true}',
                    status=429,
                    mimetype='application/json'
                )

            # Aggressive cleanup to prevent memory leak
            if now - _ddos_last_cleanup > 30 or len(_ddos_ip_counts) > DDOS_MAX_TRACKED_IPS:
                _ddos_last_cleanup = now
                # Remove old entries
                for ip in list(_ddos_ip_counts.keys()):
                    _ddos_ip_counts[ip] = [t for t in _ddos_ip_counts[ip] if now - t < 10]
                    if not _ddos_ip_counts[ip]:
                        del _ddos_ip_counts[ip]
                # Remove expired blocks
                for ip in list(_ddos_block_time.keys()):
                    if now > _ddos_block_time[ip]:
                        _ddos_blocked_ips.discard(ip)
                        del _ddos_block_time[ip]
                # Also cleanup request_counts
                _cleanup_request_counts()

            return None
        except Exception as e:
            print(f"[DDOS] protection error: {e}")
            return None

    @app.before_request
    def _maybe_init_background():
        try:
            # CPU OPTIMIZATION: Skip quickly if already initialized
            if _INIT_BACKGROUND_DONE:
                return
            _init_background()
        except Exception as e:
            log.error(f"_maybe_init_background failed: {e}")
            return None

    @app.route('/startup_diag')
    def startup_diag():
        """Expose current diagnostic snapshot (no secrets)."""
        try:
            info = {
                'pid': os.getpid(),
                'python': sys.version.split()[0],
                'platform': platform.platform(),
                'channels': CHANNELS,
                'authorized': AUTH_STATUS,
                'messages_file_exists': os.path.exists(MESSAGES_FILE),
                'messages_count': len(load_messages()),
                'fetch_thread_started': FETCH_THREAD_STARTED,
                'session_present': bool(session_str),
                'retention_minutes': MESSAGES_RETENTION_MINUTES,
                'retention_max_count': MESSAGES_MAX_COUNT,
                'subscribers': len(SUBSCRIBERS),
                'cache_stats': RESPONSE_CACHE.stats(),  # HIGH-LOAD: Cache statistics
            }
            return jsonify(info)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cache-stats')
    def cache_stats():
        """Get response cache statistics for monitoring."""
        stats = RESPONSE_CACHE.stats()
        # Also clean expired entries
        cleaned = RESPONSE_CACHE.clear_expired()
        stats['expired_cleaned'] = cleaned
        return jsonify(stats)


    @app.route('/healthz')
    def healthz():
        """Lightweight health endpoint for uptime monitors."""
        try:
            messages = load_messages()
            file_exists = os.path.exists(MESSAGES_FILE)
            latest_date = None
            for m in messages:
                candidate = m.get('date')
                if candidate and (latest_date is None or candidate > latest_date):
                    latest_date = candidate
            payload = {
                'status': 'ok',
                'messages_count': len(messages),
                'manual_count': sum(1 for m in messages if m.get('manual')),
                'messages_file_size': os.path.getsize(MESSAGES_FILE) if file_exists else 0,
                'messages_file_present': file_exists,
                'latest_message_at': latest_date,
                'fetch_thread_started': FETCH_THREAD_STARTED,
                'backfill': BACKFILL_STATUS.copy(),
                'retention': {
                    'minutes': MESSAGES_RETENTION_MINUTES,
                    'max_count': MESSAGES_MAX_COUNT,
                },
            }
            return jsonify(payload)
        except Exception as exc:
            return jsonify({'status': 'error', 'error': str(exc)}), 500

    @app.route('/admin/test-nominatim')
    def test_nominatim():
        """Test if Nominatim is reachable from this server."""

        # Safely get settlements count
        try:
            all_settlements_count = len(UKRAINE_ALL_SETTLEMENTS) if UKRAINE_ALL_SETTLEMENTS else 0
        except:
            all_settlements_count = 0
        try:
            oblast_settlements_count = len(UKRAINE_SETTLEMENTS_BY_OBLAST) if UKRAINE_SETTLEMENTS_BY_OBLAST else 0
        except:
            oblast_settlements_count = 0

        results = {
            'nominatim': {'status': 'unknown', 'time_ms': 0, 'error': None},
            'settlements_db': {
                'all_loaded': all_settlements_count,
                'oblast_aware_loaded': oblast_settlements_count,
            },
            'memory_optimized': os.environ.get('MEMORY_OPTIMIZED', 'false'),
        }

        # Test Nominatim
        try:
            start = time_module.time()
            nominatim_url = 'https://nominatim.openstreetmap.org/search'
            params = {'q': 'Kyiv, Ukraine', 'format': 'json', 'limit': 1}
            headers = {'User-Agent': 'neptun.in.ua/1.0'}
            response = requests.get(nominatim_url, params=params, headers=headers, timeout=5)
            elapsed = (time_module.time() - start) * 1000

            results['nominatim']['time_ms'] = round(elapsed, 1)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    results['nominatim']['status'] = 'ok'
                    results['nominatim']['result'] = data[0].get('display_name', '')[:50]
                else:
                    results['nominatim']['status'] = 'empty_response'
            else:
                results['nominatim']['status'] = f'http_{response.status_code}'
        except requests.exceptions.Timeout:
            results['nominatim']['status'] = 'timeout'
            results['nominatim']['error'] = 'Request timed out after 5s'
        except requests.exceptions.ConnectionError as e:
            results['nominatim']['status'] = 'connection_error'
            results['nominatim']['error'] = str(e)[:200]
        except Exception as e:
            results['nominatim']['status'] = 'error'
            results['nominatim']['error'] = str(e)[:200]

        return jsonify(results)

    # Manual trigger (idempotent) if needed before first page hit
    @app.route('/startup_init', methods=['POST'])
    def startup_init():
        _init_background()
        return jsonify({'status': 'ok'})

    # BANDWIDTH PROTECTION: Custom static route will compete with Flask's built-in route
    # Flask will prioritize our custom route due to specificity


    # Force reload endpoints for admin
    @app.route('/api/force-reload-status')
    def force_reload_status():
        """Check if force reload flag is active"""
        global FORCE_RELOAD_TIMESTAMP
        with FORCE_RELOAD_LOCK:
            current_time = time.time()
            # Check if force reload is still active (within duration window)
            should_reload = (FORCE_RELOAD_TIMESTAMP > 0 and
                            (current_time - FORCE_RELOAD_TIMESTAMP) < FORCE_RELOAD_DURATION)
        return jsonify({'reload': should_reload})

    @app.route('/admin/trigger-force-reload', methods=['POST'])
    def trigger_force_reload():
        """Admin endpoint to trigger force reload for all users"""
        if not _require_secret(request):
            return Response('Forbidden', status=403)

        global FORCE_RELOAD_TIMESTAMP
        with FORCE_RELOAD_LOCK:
            FORCE_RELOAD_TIMESTAMP = time.time()

        log.info(f"🔄 ADMIN: Force reload triggered for all users (active for {FORCE_RELOAD_DURATION} seconds)")
        return jsonify({'success': True, 'message': f'Force reload activated for {FORCE_RELOAD_DURATION} seconds'})


    # ========== Firebase Cloud Messaging Endpoints ==========

    @app.route('/api/register-device', methods=['POST'])
    def register_device():
        """Register a device for push notifications."""
        try:
            data = request.get_json()
            token = data.get('token')
            regions = data.get('regions', [])
            oblast_ids = data.get('oblast_ids', [])
            raion_ids = data.get('raion_ids', [])
            device_id = data.get('device_id', token)
            enabled = data.get('enabled', True)  # Support disabling notifications
            platform = data.get('platform', 'unknown')  # iOS/Android

            if not token and not device_id:
                return jsonify({'error': 'Missing token or device_id'}), 400

            # Log registration with platform info
            log.info(
                f"📱 Device registration: platform={platform}, device_id={device_id[:20]}..., regions={regions[:3]}..., oblast_ids={oblast_ids[:3]}..., raion_ids={raion_ids[:3]}..."
            )
            print(
                f"[REGISTER] platform={platform}, token_prefix={token[:30] if token else 'None'}..., regions={regions}, oblast_ids={oblast_ids}, raion_ids={raion_ids}",
                flush=True,
            )

            # If notifications disabled or no regions, remove device
            if not enabled or not regions:
                device_store.remove_device(device_id)
                log.info(f"Device {device_id[:20]}... unregistered (notifications disabled)")
                return jsonify({'success': True, 'device_id': device_id, 'status': 'unregistered'})

            # Derive IDs on server if client didn't send them
            if not oblast_ids or not raion_ids:
                derived_oblasts, derived_raions = _derive_region_ids_from_regions(regions)
                if not oblast_ids and derived_oblasts:
                    oblast_ids = derived_oblasts
                if not raion_ids and derived_raions:
                    raion_ids = derived_raions

            device_store.register_device(
                token,
                regions,
                device_id,
                oblast_ids=oblast_ids,
                raion_ids=raion_ids,
            )
            return jsonify({'success': True, 'device_id': device_id, 'platform': platform})
        except Exception as e:
            log.error(f"Error registering device: {e}")
            return jsonify({'error': str(e)}), 500


    @app.route('/api/update-regions', methods=['POST'])
    def update_regions():
        """Update regions for an existing device."""
        try:
            data = request.get_json()
            device_id = data.get('device_id')
            regions = data.get('regions', [])
            oblast_ids = data.get('oblast_ids', [])
            raion_ids = data.get('raion_ids', [])

            if not device_id or not regions:
                return jsonify({'error': 'Missing device_id or regions'}), 400

            if not oblast_ids or not raion_ids:
                derived_oblasts, derived_raions = _derive_region_ids_from_regions(regions)
                if not oblast_ids and derived_oblasts:
                    oblast_ids = derived_oblasts
                if not raion_ids and derived_raions:
                    raion_ids = derived_raions

            device_store.update_regions(device_id, regions, oblast_ids=oblast_ids, raion_ids=raion_ids)
            return jsonify({'success': True})
        except Exception as e:
            log.error(f"Error updating regions: {e}")
            return jsonify({'error': str(e)}), 500


    @app.route('/api/registered-devices', methods=['GET'])
    def get_registered_devices():
        """Get all registered devices (for debugging)."""
        try:
            devices = device_store._load()
            # Mask tokens for security (show only last 10 chars) but show length
            for _device_id, data in devices.items():
                if 'token' in data:
                    token = data['token']
                    data['token_length'] = len(token)
                    data['token'] = '...' + token[-10:] if len(token) > 10 else token
            return jsonify({
                'count': len(devices),
                'devices': devices
            })
        except Exception as e:
            log.error(f"Error getting devices: {e}")
            return jsonify({'error': str(e)}), 500


    @app.route('/api/test-push/<token>', methods=['POST'])
    def test_push_to_token(token):
        """Send a test push notification directly to a specific FCM token (for debugging)."""
        if not firebase_initialized:
            return jsonify({'error': 'Firebase not initialized'}), 500
    
        try:
            from firebase_admin import messaging
        
            title = request.json.get('title', '🧪 Test Push') if request.is_json else '🧪 Test Push'
            body = request.json.get('body', 'Тестове сповіщення для перевірки push') if request.is_json else 'Тестове сповіщення для перевірки push'
        
            message = messaging.Message(
                data={
                    'type': 'test',
                    'title': title,
                    'body': body,
                    'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
                },
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        icon='ic_notification',
                        channel_id='critical_alerts',
                    ),
                ),
                apns=messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'alert',
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(title=title, body=body),
                            sound='default',
                            badge=1,
                        ),
                    ),
                ),
                token=token,
            )
        
            response = messaging.send(message)
            log.info(f"✅ Test push sent to token {token[:20]}...: {response}")
            return jsonify({'success': True, 'response': response})
        except Exception as e:
            log.error(f"❌ Test push failed: {e}")
            return jsonify({'error': str(e)}), 500


    # ============ FEEDBACK / BUG REPORTS ============
    # Ensure we use persistent storage for feedback
    if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR):
        FEEDBACK_FILE = os.path.join(PERSISTENT_DATA_DIR, 'feedback.json')
        log.info(f'Feedback will be saved to persistent storage: {FEEDBACK_FILE}')
    else:
        FEEDBACK_FILE = 'feedback.json'
        log.warning(f'Feedback will be saved locally (not persistent): {FEEDBACK_FILE}')

    def load_feedback():
        """Load feedback messages."""
        try:
            if os.path.exists(FEEDBACK_FILE):
                with open(FEEDBACK_FILE, encoding='utf-8') as f:
                    data = json.load(f)
                    log.info(f"Loaded {len(data)} feedback items from {FEEDBACK_FILE}")
                    return data
        except Exception as e:
            log.error(f"Error loading feedback: {e}")
        return []

    def save_feedback(feedback_list):
        """Save feedback messages."""
        try:
            # Ensure directory exists
            feedback_dir = os.path.dirname(FEEDBACK_FILE)
            if feedback_dir and not os.path.exists(feedback_dir):
                os.makedirs(feedback_dir, exist_ok=True)

            with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
                json.dump(feedback_list, f, ensure_ascii=False, indent=2)
            log.info(f"Saved {len(feedback_list)} feedback items to {FEEDBACK_FILE}")
        except Exception as e:
            log.error(f"Error saving feedback: {e}")

    @app.route('/api/feedback', methods=['POST'])
    def submit_feedback():
        """Submit user feedback or bug report."""
        try:
            data = request.get_json()
            message = data.get('message', '').strip()
            feedback_type = data.get('type', 'bug')  # 'bug', 'suggestion', 'other'
            device_id = data.get('device_id', '')
            device = data.get('device', '')  # iOS, Android, etc
            app_version = data.get('app_version', '')
            regions = data.get('regions', [])  # User's selected regions

            if not message:
                return jsonify({'error': 'Message is required'}), 400

            if len(message) > 5000:
                message = message[:5000]

            # Create feedback entry
            kyiv_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(kyiv_tz)

            feedback_entry = {
                'id': str(uuid.uuid4()),
                'type': feedback_type,
                'message': message,
                'device': device,
                'device_id': device_id[:50] if device_id else '',
                'app_version': app_version,
                'regions': regions[:10] if isinstance(regions, list) else [],  # Max 10 regions
                'timestamp': now.timestamp(),
                'date': now.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'new'
            }

            # Load, append, save
            feedback_list = load_feedback()
            feedback_list.append(feedback_entry)
            # Keep only last 500 entries
            if len(feedback_list) > 500:
                feedback_list = feedback_list[-500:]
            save_feedback(feedback_list)

            log.info(f"📩 New feedback received: {feedback_type} - {message[:50]}...")

            return jsonify({
                'success': True,
                'message': 'Дякуємо за ваш відгук!'
            })
        except Exception as e:
            log.error(f"Error submitting feedback: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/feedback', methods=['GET'])
    def get_feedback():
        """Get all feedback (for admin) with nice HTML interface."""
        try:
            # Simple auth check
            auth_key = request.args.get('key', '')
            if auth_key != os.getenv('ADMIN_KEY', 'neptun_admin_2024'):
                return jsonify({'error': 'Unauthorized'}), 401

            feedback_list = load_feedback()

            # Check if JSON format requested
            if request.args.get('format') == 'json':
                return jsonify({
                    'success': True,
                    'feedback': feedback_list,
                    'count': len(feedback_list)
                })

            # Sort by date (newest first)
            feedback_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Generate HTML
            html = '''<!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NEPTUN - Зворотній зв'язок</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                min-height: 100vh;
                color: #e0e0e0;
                padding: 20px;
            }

            .container {
                max-width: 900px;
                margin: 0 auto;
            }

            header {
                text-align: center;
                padding: 30px 0;
                margin-bottom: 30px;
            }

            h1 {
                font-size: 2.5rem;
                background: linear-gradient(90deg, #00d4ff, #7b2ff7);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
            }

            .stats {
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-bottom: 30px;
            }

            .stat-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 20px 40px;
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            .stat-number {
                font-size: 2.5rem;
                font-weight: bold;
                color: #00d4ff;
            }

            .stat-label {
                font-size: 0.9rem;
                color: #888;
                margin-top: 5px;
            }

            .feedback-list {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .feedback-card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 25px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .feedback-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 40px rgba(0, 212, 255, 0.1);
                border-color: rgba(0, 212, 255, 0.3);
            }

            .feedback-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 15px;
            }

            .feedback-meta {
                display: flex;
                flex-direction: column;
                gap: 5px;
            }

            .feedback-device {
                font-size: 0.85rem;
                color: #888;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .feedback-device .icon {
                font-size: 1.1rem;
            }

            .feedback-time {
                font-size: 0.8rem;
                color: #666;
                background: rgba(255, 255, 255, 0.05);
                padding: 5px 12px;
                border-radius: 20px;
            }

            .feedback-text {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 12px;
                padding: 20px;
                font-size: 1rem;
                line-height: 1.6;
                color: #f0f0f0;
                white-space: pre-wrap;
                word-break: break-word;
            }

            .feedback-regions {
                margin-top: 15px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .region-tag {
                background: linear-gradient(135deg, #7b2ff7 0%, #f107a3 100%);
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 500;
            }

            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #666;
            }

            .empty-state .icon {
                font-size: 4rem;
                margin-bottom: 20px;
            }

            .refresh-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: linear-gradient(135deg, #00d4ff 0%, #7b2ff7 100%);
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 30px;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 600;
                box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3);
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .refresh-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 6px 30px rgba(0, 212, 255, 0.4);
            }

            @media (max-width: 600px) {
                h1 { font-size: 1.8rem; }
                .stats { flex-direction: column; gap: 15px; }
                .stat-card { padding: 15px 30px; }
                .feedback-header { flex-direction: column; gap: 10px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🌊 NEPTUN Feedback</h1>
                <p style="color: #888;">Адмін-панель зворотнього зв'язку</p>
                <p style="color: #555; font-size: 0.8rem; margin-top: 5px;">💾 ''' + ('Persistent: ' + FEEDBACK_FILE if '/data' in FEEDBACK_FILE else '⚠️ Local: ' + FEEDBACK_FILE) + '''</p>
            </header>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">''' + str(len(feedback_list)) + '''</div>
                    <div class="stat-label">Всього повідомлень</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">''' + str(len([f for f in feedback_list if str(f.get('timestamp', ''))[:10] == datetime.now().strftime('%Y-%m-%d')])) + '''</div>
                    <div class="stat-label">Сьогодні</div>
                </div>
            </div>

            <div class="feedback-list">'''

            if not feedback_list:
                html += '''
                <div class="empty-state">
                    <div class="icon">📭</div>
                    <h3>Поки немає повідомлень</h3>
                    <p>Користувачі ще не надіслали зворотній зв'язок</p>
                </div>'''
            else:
                for fb in feedback_list:
                    # Get device info
                    device = fb.get('device', '') or fb.get('device_id', '') or 'Невідомий пристрій'
                    app_version = fb.get('app_version', '')
                    feedback_type = fb.get('type', 'bug')

                    # Determine device icon
                    if 'iphone' in device.lower() or 'ios' in device.lower():
                        device_icon = '📱'
                    elif 'android' in device.lower():
                        device_icon = '🤖'
                    else:
                        device_icon = '💻'

                    # Type badge
                    type_badge = {'bug': '🐛 Баг', 'suggestion': '💡 Ідея', 'other': '📝 Інше'}.get(feedback_type, '📝')

                    # Format timestamp
                    ts = fb.get('timestamp', '')
                    try:
                        if isinstance(ts, (int, float)):
                            # Unix timestamp
                            dt = datetime.fromtimestamp(ts)
                            formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                        elif isinstance(ts, str) and ts:
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                        else:
                            formatted_time = fb.get('date', 'Невідомо')
                    except:
                        formatted_time = fb.get('date', str(ts)[:16] if ts else 'Невідомо')

                    # Escape HTML in text - use 'message' field!
                    text = fb.get('message', '') or fb.get('text', '')
                    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    device_display = f"{device}" + (f" (v{app_version})" if app_version else "")
                    device_escaped = device_display.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                    # Get regions
                    regions = fb.get('regions', [])

                    html += f'''
                <div class="feedback-card">
                    <div class="feedback-header">
                        <div class="feedback-meta">
                            <div class="feedback-device">
                                <span class="icon">{device_icon}</span>
                                <span>{device_escaped}</span>
                                <span style="margin-left: 10px; background: rgba(255,255,255,0.1); padding: 3px 8px; border-radius: 10px; font-size: 0.75rem;">{type_badge}</span>
                            </div>
                        </div>
                        <div class="feedback-time">🕐 {formatted_time}</div>
                    </div>
                    <div class="feedback-text">{text if text else "<i style='color:#666'>Порожнє повідомлення</i>"}</div>'''

                    if regions:
                        html += '''
                    <div class="feedback-regions">'''
                        for region in regions[:5]:  # Show max 5 regions
                            region_escaped = region.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            html += f'''
                        <span class="region-tag">📍 {region_escaped}</span>'''
                        if len(regions) > 5:
                            html += f'''
                        <span class="region-tag">+{len(regions) - 5} ще</span>'''
                        html += '''
                    </div>'''

                    html += '''
                </div>'''

            html += '''
            </div>
        </div>

        <button class="refresh-btn" onclick="location.reload()">🔄 Оновити</button>
    </body>
    </html>'''

            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

        except Exception as e:
            return jsonify({'error': str(e)}), 500


    @app.route('/api/test-notification', methods=['POST'])
    def test_notification():
        """Send a test notification to a device."""
        if not firebase_initialized:
            return jsonify({'error': 'Firebase not initialized'}), 500

        try:
            from firebase_admin import messaging

            data = request.get_json()
            token = data.get('token')
            device_id = data.get('device_id')
            title = data.get('title', '🧪 Тестове сповіщення')
            body = data.get('body', 'NEPTUN працює коректно!')
            region = data.get('region', 'Тест')

            # If device_id provided, look up the token
            if not token and device_id:
                devices = device_store._load()
                device_data = devices.get(device_id)
                if device_data:
                    token = device_data.get('token')

            if not token:
                return jsonify({'error': 'Missing token or device_id'}), 400

            # For Android: DATA-ONLY message (no notification) so background handler processes TTS
            message = messaging.Message(
                # NO notification block for Android - only data!
                data={
                    'type': 'alarm',
                    'title': title,
                    'body': body,
                    'region': region,
                    'alarm_state': 'active',
                    'is_critical': 'true',
                    'timestamp': datetime.now(pytz.UTC).isoformat(),
                },
                android=messaging.AndroidConfig(
                    priority='high',
                ),
                token=token,
            )

            response = messaging.send(message)
            log.info(f"Test notification sent successfully: {response}")
            return jsonify({'success': True, 'message_id': response})
            return jsonify({'success': True, 'message_id': response})
        except messaging.UnregisteredError:
            # Token is invalid - remove device from store
            log.warning("Token is invalid (UnregisteredError), removing device...")
            device_store.remove_device(token)
            return jsonify({'error': 'NotRegistered', 'message': 'Token is invalid and was removed. Please re-register the device.'}), 410
        except Exception as e:
            error_msg = str(e)
            if 'NotRegistered' in error_msg or 'not registered' in error_msg.lower():
                log.warning("Token not registered, removing device...")
                device_store.remove_device(token)
                return jsonify({'error': 'NotRegistered', 'message': 'Token is invalid and was removed. Please re-register the device.'}), 410
            log.error(f"Error sending test notification: {e}")
            return jsonify({'error': str(e)}), 500


    @app.route('/api/test-ios-push', methods=['POST'])
    def test_ios_push():
        """Send a test push notification to iOS device with full APNs config."""
        if not firebase_initialized:
            return jsonify({'error': 'Firebase not initialized'}), 500

        try:
            from firebase_admin import messaging

            data = request.get_json() or {}
            token = data.get('token')

            if not token:
                return jsonify({'error': 'Missing token parameter'}), 400

            log.info(f"=== TEST iOS PUSH to token: {token[:50]}... ===")

            # Full iOS push with APNs config (like telegram_threat)
            message = messaging.Message(
                data={
                    'type': 'telegram_threat',
                    'title': '🧪 ТЕСТ iOS Push',
                    'body': 'Якщо ви бачите це - APNs працює!',
                    'location': 'Тест',
                    'region': 'Тест',
                    'alarm_state': 'active',
                    'is_critical': 'true',
                    'threat_type': 'Тестове сповіщення',
                    'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
                },
                apns=messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'alert',
                        'apns-expiration': '0',
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title='🧪 ТЕСТ iOS Push',
                                body='Якщо ви бачите це - APNs працює!'
                            ),
                            sound='default',
                            badge=1,
                            content_available=True,
                            mutable_content=True,
                        ),
                    ),
                ),
                token=token,
            )

            response = messaging.send(message)
            log.info(f"✅ Test iOS push sent: {response}")
            return jsonify({'success': True, 'message_id': response})

        except messaging.UnregisteredError as e:
            log.error(f"Token unregistered: {e}")
            return jsonify({'error': 'Token unregistered - device needs to re-register'}), 410
        except Exception as e:
            log.error(f"Error sending iOS test push: {e}")
            return jsonify({'error': str(e)}), 500


    @app.route('/api/test-telegram-threat', methods=['POST'])
    def test_telegram_threat():
        """Send a test telegram_threat notification to all_regions topic AND specific token."""
        if not firebase_initialized:
            return jsonify({'error': 'Firebase not initialized'}), 500

        try:
            from firebase_admin import messaging

            data = request.get_json() or {}
            token = data.get('token')  # Optional: send to specific device
            region = data.get('region', 'Київська область')
            threat_type = data.get('threat_type', 'Тестова загроза')

            title = f"🧪 ТЕСТ: {region}"
            body = f"Тестове telegram_threat повідомлення - {threat_type}"

            timestamp = datetime.now(pytz.timezone('Europe/Kiev')).isoformat()

            # Build APNs config
            apns_config = messaging.APNSConfig(
                headers={
                    'apns-priority': '10',
                    'apns-push-type': 'alert',
                    'apns-expiration': '0',
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        sound='default',
                        badge=1,
                        content_available=True,
                        mutable_content=True,
                    ),
                ),
            )

            android_config = messaging.AndroidConfig(
                priority='high',
                ttl=timedelta(seconds=300),
            )

            fcm_data = {
                'type': 'telegram_threat',
                'title': title,
                'body': body,
                'location': region,
                'region': region,
                'alarm_state': 'active',
                'is_critical': 'false',
                'threat_type': threat_type,
                'timestamp': timestamp,
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            }

            results = []

            # 1. Send to all_regions topic
            try:
                topic_message = messaging.Message(
                    data=fcm_data,
                    android=android_config,
                    apns=apns_config,
                    topic='all_regions',
                )
                response = messaging.send(topic_message)
                results.append({'target': 'topic:all_regions', 'success': True, 'response': response})
                log.info(f"✅ Test telegram_threat sent to all_regions: {response}")
            except Exception as e:
                results.append({'target': 'topic:all_regions', 'success': False, 'error': str(e)})
                log.error(f"❌ Failed to send to all_regions: {e}")

            # 2. If token provided, also send directly to device
            if token:
                try:
                    token_message = messaging.Message(
                        data=fcm_data,
                        android=android_config,
                        apns=apns_config,
                        token=token,
                    )
                    response = messaging.send(token_message)
                    results.append({'target': f'token:{token[:20]}...', 'success': True, 'response': response})
                    log.info(f"✅ Test telegram_threat sent to token: {response}")
                except Exception as e:
                    results.append({'target': f'token:{token[:20]}...', 'success': False, 'error': str(e)})
                    log.error(f"❌ Failed to send to token: {e}")

            return jsonify({'success': True, 'results': results})

        except Exception as e:
            log.error(f"Error in test_telegram_threat: {e}")
            return jsonify({'error': str(e)}), 500


    def send_fcm_notification(message_data: dict):
        """Send FCM notification for a new threat message."""
        if not firebase_initialized:
            log.warning("Firebase not initialized, skipping notifications")
            return

        try:
            import re

            from firebase_admin import messaging

            # Check if this is a real threat (not just informational message)
            threat_type = message_data.get('threat_type', '') or message_data.get('type', '') or ''
            text = message_data.get('text', '') or ''
            text_lower = text.lower()

            # Check if this is an "all clear" message (відбій)
            is_all_clear = any(kw in text_lower for kw in ['відбій', 'скасовано', 'завершено'])

            # Skip only truly informational messages (not відбій - we want to notify about all clear too)
            skip_keywords = ['немає загрози', 'безпечно', 'інформація', 'увага!', 'попередження']
            if any(kw in text_lower for kw in skip_keywords):
                log.info(f"Skipping FCM for informational message: {text[:50]}...")
                return

            # Skip if no threat type detected AND not an all clear message
            if not threat_type and not is_all_clear:
                log.info("Skipping FCM for message without threat type")
                return

            # Use 'place' field for location (it's the geocoded place name)
            location = message_data.get('place', '') or message_data.get('location', '') or ''

            # CRITICAL: Extract specific city from place or text if format is "City (Oblast обл.)"
            # Example: "Овруч (Житомирська обл.)" -> city = "Овруч"
            city_from_text = ''
        
            # First try to extract from place field (more reliable)
            if location and '(' in location:
                city_from_place = location.split('(')[0].strip()
                if city_from_place:
                    city_from_text = city_from_place
                    log.info(f"Extracted city from place: '{city_from_text}' (full place: {location})")
        
            # Fallback: try to extract from text
            if not city_from_text and text:
                # Pattern: "City (Oblast обл.)" - extract city before parentheses
                city_oblast_match = re.search(r'^[^а-яіїєґА-ЯІЇЄҐ]*([А-ЯІЇЄҐа-яіїєґ][а-яіїєґА-ЯІЇЄҐ\'\-\s]+?)\s*\([^)]*обл[^)]*\)', text)
                if city_oblast_match:
                    city_from_text = city_oblast_match.group(1).strip()
                    # Clean up emoji and special chars at the beginning
                    city_from_text = re.sub(r'^[^\w\s]+\s*', '', city_from_text).strip()
                    log.info(f"Extracted city from text: '{city_from_text}' (full text: {text[:80]})")

            # Use extracted city if available and long enough (>= 5 chars), otherwise fall back to place/region
            # This prevents "Кам" instead of "Каменське"
            if city_from_text and len(city_from_text) >= 5:
                specific_location = city_from_text
            elif location and len(location) >= 3:
                specific_location = location
            else:
                specific_location = ''

            if not specific_location and not location:
                log.info("Skipping FCM for message without place")
                return

            log.info("=== FCM NOTIFICATION TRIGGERED ===")
            log.info(f"Place (original): {location}")
            log.info(f"City (extracted): {city_from_text}")
            log.info(f"Location for TTS (min 5 chars): {specific_location}")
            log.info(f"Threat type: {threat_type}")

            # Find matching region - search in place field AND in text for oblast pattern
            # to handle "Овруч (Житомирська обл.)" format
            region = None
            place_lower = location.lower()
            text_for_region = text.lower() if text else ''

            # First try to extract region from text with "(Oblast обл.)" pattern
            oblast_in_text = re.search(r'\(([а-яіїєґ]+ська)\s+обл\.?\)', text_for_region)
            if oblast_in_text:
                oblast_adj = oblast_in_text.group(1)  # e.g., "житомирська"
                log.info(f"Found oblast in text: {oblast_adj}")

            # Region mapping - keywords to match ONLY in place name
            regions_map = {
                'Київ': ['київ', 'києв'],
                'Київська область': ['київська обл', 'київська', 'київщин', 'бориспіль', 'бровар', 'ірпін', 'буча', 'вишгород', 'фастів', 'біла церква'],
                'Дніпропетровська область': ['дніпропетровська', 'дніпропетровськ', 'дніпро', 'кривий ріг', 'кам\'янськ', 'нікополь', 'павлоград'],
                'Харківська область': ['харківська', 'харків', 'харьков', 'ізюм', 'куп\'янськ', 'чугуїв', 'лозова'],
                'Одеська область': ['одеська', 'одес', 'одещин', 'ізмаїл', 'білгород-дністровськ', 'чорноморськ'],
                'Львівська область': ['львівська', 'львів', 'львівщин', 'дрогобич', 'стрий', 'червоноград'],
                'Донецька область': ['донецька', 'донецьк', 'донеч', 'маріуполь', 'краматорськ', 'слов\'янськ', 'бахмут', 'покровськ'],
                'Запорізька область': ['запорізька', 'запоріж', 'мелітополь', 'бердянськ', 'енергодар'],
                'Вінницька область': ['вінницька', 'вінниц', 'жмеринка', 'козятин', 'хмільник'],
                'Житомирська область': ['житомирська', 'житомир', 'бердичів', 'коростень', 'новоград', 'овруч'],
                'Черкаська область': ['черкаська', 'черкас', 'умань', 'сміла', 'золотоноша'],
                'Чернігівська область': ['чернігівська', 'чернігів', 'чернігов', 'ніжин', 'прилуки', 'корюків'],
                'Чернівецька область': ['чернівецька', 'чернівці', 'чернівц', 'чернівеч', 'буковина', 'новодністровськ', 'вижниця', 'сторожинець'],
                'Полтавська область': ['полтавська', 'полтав', 'кременчук', 'миргород', 'лубни'],
                'Сумська область': ['сумська', 'сум', 'конотоп', 'шостка', 'ромни', 'охтирка'],
                'Миколаївська область': ['миколаївська', 'миколаїв', 'миколаєв', 'первомайськ', 'вознесенськ'],
                'Херсонська область': ['херсонська', 'херсон', 'нова каховка', 'каховка'],
                'Кіровоградська область': ['кіровоградська', 'кіровоград', 'кропивниц', 'олександрія', 'знам\'янка'],
                'Хмельницька область': ['хмельницька', 'хмельниц', 'кам\'янець-подільськ', 'шепетівка'],
                'Рівненська область': ['рівненська', 'рівн', 'рівне', 'дубно', 'костопіль', 'дубровиц'],
                'Волинська область': ['волинська', 'волин', 'луцьк', 'ковель', 'нововолинськ'],
                'Тернопільська область': ['тернопільська', 'тернопіль', 'чортків', 'кременець'],
                'Івано-Франківська область': ['івано-франківська', 'івано-франків', 'калуш', 'коломия', 'надвірна'],
                'Закарпатська область': ['закарпатська', 'закарпат', 'ужгород', 'мукачево', 'хуст', 'берегово'],
                'Луганська область': ['луганська', 'луганськ', 'луганщин', 'сєвєродонецьк', 'лисичанськ'],
            }

            # First search in text for oblast pattern (most reliable for "City (Oblast обл.)" format)
            # IMPORTANT: Search for LONGEST matching keyword first to avoid confusion
            # between similar names like "Чернівці" vs "Чернігів"
            best_match = None
            best_keyword_len = 0

            for region_name, keywords in regions_map.items():
                for keyword in keywords:
                    if keyword in text_for_region:
                        # Prefer longer (more specific) matches
                        if len(keyword) > best_keyword_len:
                            best_match = region_name
                            best_keyword_len = len(keyword)
                            log.info(f"Found potential match: {region_name} (keyword: '{keyword}', len={len(keyword)})")

            if best_match:
                region = best_match
                log.info(f"Best match from text: {region} (keyword length: {best_keyword_len})")

            # Fallback: search in place field
            if not region:
                best_match = None
                best_keyword_len = 0
                for region_name, keywords in regions_map.items():
                    for keyword in keywords:
                        if keyword in place_lower:
                            if len(keyword) > best_keyword_len:
                                best_match = region_name
                                best_keyword_len = len(keyword)
                                log.info(f"Found potential match from place: {region_name} (keyword: '{keyword}')")
                if best_match:
                    region = best_match
                    log.info(f"Best match from place: {region}")

            if not region:
                log.info(f"Could not determine region for place: {location}")
                return

            # Resolve ID-based region identifiers for strict client filtering
            place_for_ids = specific_location or location
            oblast_id, raion_id = get_region_ids_from_place(place_for_ids, region)
            if oblast_id:
                log.info(f"Resolved oblast_id={oblast_id} for region={region}")
            if raion_id:
                log.info(f"Resolved raion_id={raion_id} for place={place_for_ids}")

            # Determine if critical
            threat_lower = threat_type.lower()
            is_critical = any(kw in threat_lower for kw in ['ракет', 'балістич', 'kab', 'cruise', 'ballistic'])

            # Map internal threat codes to human-readable Ukrainian text for TTS
            threat_type_map = {
                'alarm': 'Повітряна тривога',
                'alarm_cancel': 'Відбій тривоги',
                'shahed': 'Загроза БПЛА',
                'raketa': 'Загроза ракетної атаки',
                'kab': 'Загроза КАБ',
                'fpv': 'Загроза FPV-дронів',
                'avia': 'Загроза авіаційної атаки',
                'vibuh': 'Вибухи',
                'artillery': 'Загроза обстрілу',
                'rozved': 'Розвідувальні дрони',
                'pusk': 'Пуски дронів',
                'vidboi': 'Відбій',
                'rszv': 'Загроза РСЗВ',
            }

            # Get human-readable threat type for notifications
            readable_threat_type = threat_type_map.get(threat_type, threat_type) if threat_type else ''

            # Create notification - different format for all clear vs threat
            if is_all_clear:
                title = "🟢 Відбій тривоги"
                body = f"{specific_location}"
                alarm_state = 'ended'
                readable_threat_type = 'Відбій тривоги'
            else:
                title = f"{'🚨' if is_critical else '⚠️'} {readable_threat_type}"
                body = f"{specific_location}"
                alarm_state = 'active'

            # Send to Firebase topic for this region (using global REGION_TOPIC_MAP)
            topic = REGION_TOPIC_MAP.get(region)
            if not topic:
                log.warning(f"No topic mapping for region: {region}")
                return

            log.info(f"Sending FCM to topic: {topic}")

            # Send via topic (reaches all subscribed devices at once)
            # CRITICAL: Use DATA-ONLY message (no notification block) so Flutter can filter by region!
            # If we include notification={}, Android shows it automatically bypassing Flutter filtering
            try:
                data_payload = {
                    'type': 'all_clear' if is_all_clear else ('rocket' if is_critical else 'drone'),
                    'title': title,  # Include title in data for Flutter to show
                    'location': location,  # FULL place with city AND region for filtering
                    'body': specific_location,  # City for TTS display
                    'threat_type': readable_threat_type if readable_threat_type else 'Повітряна тривога',
                    'region': region,
                    'alarm_state': alarm_state,
                    'is_critical': 'true' if is_critical else 'false',
                    'timestamp': message_data.get('date', ''),
                    'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                }

                if oblast_id:
                    data_payload['oblast_id'] = oblast_id
                if raion_id:
                    data_payload['raion_id'] = raion_id

                message = messaging.Message(
                    data=data_payload,
                    android=messaging.AndroidConfig(
                        priority='high' if not is_all_clear else 'normal',
                        ttl=timedelta(seconds=300),
                        # NO notification block - Flutter handles showing notification after filtering
                    ),
                    apns=messaging.APNSConfig(
                        headers={
                            'apns-priority': '10',
                            'apns-push-type': 'background',  # background so Flutter can filter
                            'apns-expiration': '0',
                        },
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                content_available=True,  # Wake app to process
                                mutable_content=True,
                                # NO alert - Flutter shows notification after filtering
                            ),
                        ),
                    ),
                    topic=topic,  # Send to topic instead of individual token
                )

                response = messaging.send(message)
                log.info(f"✅ Topic notification sent to {topic}: {response}")
            except Exception as e:
                log.error(f"Failed to send topic notification to {topic}: {e}")

            # NOTE: Removed all_regions broadcast for regular alerts
            # Users should only receive alerts for regions they subscribed to
            # all_regions is now only used for telegram_threat notifications
            # which have their own filtering logic in the app

            log.info(f"Sent notifications for region: {region} (topic: {topic})")
        except Exception as e:
            log.error(f"Error in send_fcm_notification: {e}")


    # ============== ANONYMOUS CHAT API ==============
    MAX_SYSTEM_MESSAGES = 100  # Limit for system/service messages (reduced from 200)
    CHAT_RETENTION_DAYS = 3    # Keep user messages for 3 days (reduced from 7)
    _chat_initialized = False

    # SSE subscribers for real-time chat
    CHAT_SUBSCRIBERS = set()  # queues for chat SSE clients
    CHAT_TYPING_USERS = {}  # {deviceId: {'nickname': str, 'timestamp': float}}
    CHAT_TYPING_TTL = 5  # seconds before typing indicator expires
    MAX_SSE_SUBSCRIBERS = 100  # MEMORY PROTECTION: Limit SSE connections to prevent OOM (reduced from 200)

    # ============== CHAT RATE LIMITING ==============
    # Configurable rate limits (sliding window approach)
    CHAT_RATE_LIMIT_MESSAGES = 10  # Max messages per window
    CHAT_RATE_LIMIT_WINDOW = 60    # Window size in seconds (1 minute)
    CHAT_RATE_LIMIT_COOLDOWN = 30  # Cooldown penalty in seconds after hitting limit

    class ChatRateLimiter:
        """
        Sliding window rate limiter for chat messages.
        Tracks message timestamps per device and enforces limits.
        Thread-safe implementation.
        """
        def __init__(self, max_messages: int = 10, window_seconds: int = 60, cooldown_seconds: int = 30):
            self.max_messages = max_messages
            self.window_seconds = window_seconds
            self.cooldown_seconds = cooldown_seconds
            self._timestamps: dict = {}  # device_id -> list of timestamps
            self._cooldowns: dict = {}   # device_id -> cooldown_end_time
            self._lock = threading.RLock()
    
        def _cleanup_old_timestamps(self, device_id: str, now: float) -> list:
            """Remove timestamps outside the sliding window."""
            window_start = now - self.window_seconds
            timestamps = self._timestamps.get(device_id, [])
            return [ts for ts in timestamps if ts > window_start]
    
        def is_rate_limited(self, device_id: str) -> tuple:
            """
            Check if device is rate limited.
            Returns: (is_limited: bool, wait_seconds: int, reason: str)
            """
            if not device_id:
                return (False, 0, '')
        
            now = time.time()
        
            with self._lock:
                # Check if in cooldown period
                cooldown_end = self._cooldowns.get(device_id, 0)
                if now < cooldown_end:
                    wait = int(cooldown_end - now) + 1
                    return (True, wait, 'cooldown')
            
                # Clean up and get recent timestamps
                timestamps = self._cleanup_old_timestamps(device_id, now)
                self._timestamps[device_id] = timestamps
            
                # Check if over limit
                if len(timestamps) >= self.max_messages:
                    # Apply cooldown penalty
                    self._cooldowns[device_id] = now + self.cooldown_seconds
                    wait = self.cooldown_seconds
                    return (True, wait, 'limit_exceeded')
            
                return (False, 0, '')
    
        def record_message(self, device_id: str):
            """Record a new message timestamp for the device."""
            if not device_id:
                return
        
            now = time.time()
        
            with self._lock:
                if device_id not in self._timestamps:
                    self._timestamps[device_id] = []
                self._timestamps[device_id].append(now)
            
                # Cleanup: remove very old entries periodically
                if len(self._timestamps) > 1000:  # Reduced from 10000
                    self._cleanup_all_old_entries(now)
    
        def _cleanup_all_old_entries(self, now: float):
            """Periodic cleanup of all old entries to prevent memory growth."""
            window_start = now - self.window_seconds - 3600  # Keep extra hour buffer
            devices_to_remove = []
        
            for device_id, timestamps in self._timestamps.items():
                fresh = [ts for ts in timestamps if ts > window_start]
                if fresh:
                    self._timestamps[device_id] = fresh
                else:
                    devices_to_remove.append(device_id)
        
            for device_id in devices_to_remove:
                del self._timestamps[device_id]
                self._cooldowns.pop(device_id, None)
    
        def get_remaining(self, device_id: str) -> int:
            """Get remaining messages allowed in current window."""
            if not device_id:
                return self.max_messages
        
            now = time.time()
            with self._lock:
                timestamps = self._cleanup_old_timestamps(device_id, now)
                return max(0, self.max_messages - len(timestamps))

    # Global rate limiter instance
    _chat_rate_limiter = ChatRateLimiter(
        max_messages=CHAT_RATE_LIMIT_MESSAGES,
        window_seconds=CHAT_RATE_LIMIT_WINDOW,
        cooldown_seconds=CHAT_RATE_LIMIT_COOLDOWN
    )

    def load_chat_messages():
        """Load chat messages from file. On first call, try git pull to restore from repo."""
        global _chat_initialized
        try:
            # On first load, try to pull latest from git
            if not _chat_initialized:
                _chat_initialized = True
                try:
                    git_pull_on_startup()
                except Exception as e:
                    log.warning(f"Git pull on chat init failed: {e}")

            if os.path.exists(CHAT_MESSAGES_FILE):
                with open(CHAT_MESSAGES_FILE, encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.error(f"Error loading chat messages: {e}")
        return []

    def save_chat_messages(messages):
        """Save chat messages to file with retention policy.
    
        User messages: kept for CHAT_RETENTION_DAYS (7 days)
        System messages: limited to MAX_SYSTEM_MESSAGES (200)
        """
        try:
            # Separate user messages and system messages
            user_messages = [m for m in messages if not m.get('isSystem', False)]
            system_messages = [m for m in messages if m.get('isSystem', False)]
        
            # User messages: time-based retention (7 days)
            cutoff_ts = time.time() - (CHAT_RETENTION_DAYS * 24 * 60 * 60)
            user_messages = [m for m in user_messages if m.get('timestamp', 0) > cutoff_ts]
        
            # System messages: count-based limit (200)
            system_messages = system_messages[-MAX_SYSTEM_MESSAGES:]
        
            # Merge and sort by timestamp
            all_messages = user_messages + system_messages
            all_messages.sort(key=lambda m: m.get('timestamp', 0))
        
            with open(CHAT_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Error saving chat messages: {e}")

    @app.route('/api/chat/messages', methods=['GET'])
    def get_chat_messages():
        """Get chat messages, optionally after a specific timestamp."""
        try:
            # HIGH-LOAD OPTIMIZATION: Cache chat messages for 3 seconds
            after = request.args.get('after', '')
            limit = min(int(request.args.get('limit', 50)), 200)  # Default 50, max 200
            cache_key = f'chat_messages_{after}_{limit}'

            cached = RESPONSE_CACHE.get(cache_key)
            if cached:
                response = jsonify(cached)
                response.headers['Cache-Control'] = 'public, max-age=3'
                response.headers['X-Cache'] = 'HIT'
                return response

            messages = load_chat_messages()

            # Optional: get only messages after timestamp
            if after:
                try:
                    after_ts = float(after)
                    messages = [m for m in messages if m.get('timestamp', 0) > after_ts]
                except:
                    pass

            # Return last N messages by default
            messages = messages[-limit:]

            result = {
                'success': True,
                'messages': messages,
                'count': len(messages)
            }

            # Cache for 3 seconds
            RESPONSE_CACHE.set(cache_key, result, ttl=3)

            response = jsonify(result)
            response.headers['Cache-Control'] = 'public, max-age=3'
            response.headers['X-Cache'] = 'MISS'
            return response
        except Exception as e:
            log.error(f"Error getting chat messages: {e}")
            return jsonify({'error': str(e)}), 500

    # ============== CHAT SSE (Server-Sent Events) ==============
    def broadcast_chat_event(event_type: str, data: dict):
        """Broadcast chat event to all SSE subscribers."""
        if not CHAT_SUBSCRIBERS:
            return
        try:
            payload = json.dumps({
                'type': event_type,
                'data': data,
                'timestamp': time.time()
            }, ensure_ascii=False)
        except Exception:
            return
        dead = []
        for q in list(CHAT_SUBSCRIBERS):
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for d in dead:
            CHAT_SUBSCRIBERS.discard(d)

    @app.route('/api/chat/stream')
    def chat_stream():
        """SSE endpoint for real-time chat updates."""
        # MEMORY PROTECTION: Reject if too many subscribers
        if len(CHAT_SUBSCRIBERS) >= MAX_SSE_SUBSCRIBERS:
            log.warning(f"[CHAT_SSE] Rejected connection - limit reached ({MAX_SSE_SUBSCRIBERS})")
            return jsonify({'error': 'Server busy, please use polling'}), 503
    
        def gen():
            q = queue.Queue()
            CHAT_SUBSCRIBERS.add(q)
            last_ping = time.time()
            log.info(f"[CHAT_SSE] Client connected. Total subscribers: {len(CHAT_SUBSCRIBERS)}")
            try:
                while True:
                    try:
                        item = q.get(timeout=5)
                        yield f'data: {item}\n\n'
                    except Exception:
                        pass
                    now_t = time.time()
                    if now_t - last_ping > 25:
                        last_ping = now_t
                        yield ': ping\n\n'
            except GeneratorExit:
                pass
            finally:
                CHAT_SUBSCRIBERS.discard(q)
                log.info(f"[CHAT_SSE] Client disconnected. Total subscribers: {len(CHAT_SUBSCRIBERS)}")
    
        headers = {
            'Cache-Control': 'no-store',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
        return Response(gen(), mimetype='text/event-stream', headers=headers)

    @app.route('/api/chat/typing', methods=['POST'])
    def chat_typing():
        """Notify that user is typing."""
        try:
            data = request.get_json() or {}
            device_id = data.get('deviceId', '')
            nickname = data.get('nickname', '')
            is_typing = data.get('isTyping', True)
        
            if not device_id or not nickname:
                return jsonify({'error': 'Missing deviceId or nickname'}), 400
        
            if is_typing:
                CHAT_TYPING_USERS[device_id] = {
                    'nickname': nickname,
                    'timestamp': time.time()
                }
            else:
                CHAT_TYPING_USERS.pop(device_id, None)
        
            # Clean up expired typing indicators
            now = time.time()
            expired = [k for k, v in CHAT_TYPING_USERS.items() if now - v['timestamp'] > CHAT_TYPING_TTL]
            for k in expired:
                del CHAT_TYPING_USERS[k]
        
            # Broadcast typing status
            typing_users = [v['nickname'] for v in CHAT_TYPING_USERS.values()]
            broadcast_chat_event('typing', {'users': typing_users})
        
            return jsonify({'success': True})
        except Exception as e:
            log.error(f"Error in chat_typing: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/react', methods=['POST'])
    def chat_react():
        """Add or remove reaction to a message."""
        try:
            data = request.get_json() or {}
            message_id = data.get('messageId', '')
            device_id = data.get('deviceId', '')
            emoji = data.get('emoji', '')
            nickname = data.get('nickname', '')
        
            if not message_id or not device_id or not emoji:
                return jsonify({'error': 'Missing required fields'}), 400
        
            # Validate emoji (only allowed reactions)
            allowed_emojis = ['👍', '❤️', '😂', '😮', '😢', '🔥', '💪', '🙏']
            if emoji not in allowed_emojis:
                return jsonify({'error': 'Invalid emoji'}), 400
        
            messages = load_chat_messages()
            message = next((m for m in messages if m.get('id') == message_id), None)
        
            if not message:
                return jsonify({'error': 'Message not found'}), 404
        
            # Initialize reactions if not present
            if 'reactions' not in message:
                message['reactions'] = {}
        
            # Toggle reaction
            if emoji not in message['reactions']:
                message['reactions'][emoji] = []
        
            reaction_list = message['reactions'][emoji]
            user_reacted = next((r for r in reaction_list if r.get('deviceId') == device_id), None)
        
            if user_reacted:
                # Remove reaction
                message['reactions'][emoji] = [r for r in reaction_list if r.get('deviceId') != device_id]
                if not message['reactions'][emoji]:
                    del message['reactions'][emoji]
                action = 'removed'
            else:
                # Add reaction
                reaction_list.append({
                    'deviceId': device_id,
                    'nickname': nickname,
                    'timestamp': time.time()
                })
                action = 'added'
        
            # Clean up empty reactions
            if not message['reactions']:
                del message['reactions']
        
            save_chat_messages(messages)
        
            # Broadcast reaction update
            broadcast_chat_event('reaction', {
                'messageId': message_id,
                'emoji': emoji,
                'action': action,
                'deviceId': device_id,
                'nickname': nickname,
                'reactions': message.get('reactions', {})
            })
        
            return jsonify({
                'success': True,
                'action': action,
                'reactions': message.get('reactions', {})
            })
        except Exception as e:
            log.error(f"Error in chat_react: {e}")
            return jsonify({'error': str(e)}), 500

    # File to store registered nicknames with device IDs
    CHAT_NICKNAMES_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_nicknames.json') if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR) else 'chat_nicknames.json'
    CHAT_BANNED_USERS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_banned_users.json') if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR) else 'chat_banned_users.json'

    def load_chat_nicknames():
        """Load registered chat nicknames."""
        try:
            if os.path.exists(CHAT_NICKNAMES_FILE):
                with open(CHAT_NICKNAMES_FILE, encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.error(f"Error loading chat nicknames: {e}")
        return {}

    def save_chat_nicknames(nicknames):
        """Save registered chat nicknames."""
        try:
            with open(CHAT_NICKNAMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(nicknames, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Error saving chat nicknames: {e}")

    def load_banned_users():
        """Load banned users list."""
        try:
            if os.path.exists(CHAT_BANNED_USERS_FILE):
                with open(CHAT_BANNED_USERS_FILE, encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.error(f"Error loading banned users: {e}")
        return {}

    def save_banned_users(banned):
        """Save banned users list."""
        try:
            with open(CHAT_BANNED_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(banned, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Error saving banned users: {e}")

    def is_user_banned(device_id):
        """Check if device is banned."""
        if not device_id:
            return False
        banned = load_banned_users()
        return device_id in banned

    def is_nickname_forbidden(nickname):
        """Check if nickname contains forbidden words."""
        forbidden = ['neptun', 'нептун', 'neptune', 'admin', 'адмін', 'moderator', 'модератор', 'support', 'підтримка']
        nickname_lower = nickname.lower()
        for word in forbidden:
            if word in nickname_lower:
                return True
        return False

    @app.route('/api/chat/check-nickname', methods=['POST'])
    def check_chat_nickname():
        """Check if nickname is available and valid."""
        try:
            data = request.get_json()
            nickname = data.get('nickname', '').strip()
            device_id = data.get('deviceId', '')

            if not nickname:
                return jsonify({'available': False, 'error': 'Нікнейм не може бути порожнім'}), 400

            if len(nickname) < 3:
                return jsonify({'available': False, 'error': 'Нікнейм має бути мінімум 3 символи'}), 400

            if len(nickname) > 20:
                return jsonify({'available': False, 'error': 'Нікнейм не може бути довше 20 символів'}), 400

            # Check forbidden words
            if is_nickname_forbidden(nickname):
                return jsonify({'available': False, 'error': 'Цей нікнейм заборонено'}), 400

            # Load existing nicknames
            nicknames = load_chat_nicknames()
            nickname_lower = nickname.lower()

            # Check if nickname is taken by someone else
            for existing_nickname, owner_device_id in nicknames.items():
                if existing_nickname.lower() == nickname_lower:
                    # Allow if same device
                    if owner_device_id == device_id:
                        return jsonify({'available': True, 'message': 'Це ваш поточний нік'})
                    else:
                        return jsonify({'available': False, 'error': 'Цей нікнейм вже зайнятий'}), 400

            return jsonify({'available': True})
        except Exception as e:
            log.error(f"Error checking nickname: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/register-nickname', methods=['POST'])
    def register_chat_nickname():
        """Register a nickname for a device."""
        try:
            data = request.get_json()
            nickname = data.get('nickname', '').strip()
            device_id = data.get('deviceId', '')

            if not nickname or not device_id:
                return jsonify({'success': False, 'error': 'Missing nickname or deviceId'}), 400

            if len(nickname) < 3 or len(nickname) > 20:
                return jsonify({'success': False, 'error': 'Нікнейм має бути 3-20 символів'}), 400

            # Check forbidden words
            if is_nickname_forbidden(nickname):
                return jsonify({'success': False, 'error': 'Цей нікнейм заборонено'}), 400

            # Load existing nicknames
            nicknames = load_chat_nicknames()
            nickname_lower = nickname.lower()

            # Check if nickname is taken by someone else
            for existing_nickname, owner_device_id in nicknames.items():
                if existing_nickname.lower() == nickname_lower and owner_device_id != device_id:
                    return jsonify({'success': False, 'error': 'Цей нікнейм вже зайнятий'}), 400

            # Remove any previous nickname for this device
            nicknames = {k: v for k, v in nicknames.items() if v != device_id}

            # Register new nickname
            nicknames[nickname] = device_id
            save_chat_nicknames(nicknames)

            log.info(f"Registered chat nickname: {nickname} for device {device_id[:20]}...")

            return jsonify({'success': True, 'nickname': nickname})
        except Exception as e:
            log.error(f"Error registering nickname: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/send', methods=['POST'])
    def send_chat_message():
        """Send a new chat message."""
        try:
            data = request.get_json()

            user_id = data.get('userId', '')
            device_id = data.get('deviceId', '')
            message = data.get('message', '').strip()
            reply_to = data.get('replyTo')  # Optional reply to message id

            if not user_id or not message:
                return jsonify({'error': 'Missing userId or message'}), 400

            # Check if user is banned
            if is_user_banned(device_id):
                return jsonify({'error': 'Ви заблоковані в чаті', 'banned': True}), 403

            # Rate limiting check (skip for moderators)
            if not is_chat_moderator(device_id):
                is_limited, wait_seconds, reason = _chat_rate_limiter.is_rate_limited(device_id)
                if is_limited:
                    remaining = _chat_rate_limiter.get_remaining(device_id)
                    log.warning(f"Rate limited user {user_id[:20]} ({reason}), wait {wait_seconds}s")
                    return jsonify({
                        'error': f'Забагато повідомлень. Зачекайте {wait_seconds} сек.',
                        'rate_limited': True,
                        'wait_seconds': wait_seconds,
                        'remaining': remaining
                    }), 429

            # Validate nickname ownership if device_id provided
            if device_id:
                nicknames = load_chat_nicknames()
                registered_device = nicknames.get(user_id)
                if registered_device and registered_device != device_id:
                    return jsonify({'error': 'Цей нікнейм належить іншому користувачу'}), 403

            # Check forbidden nickname
            if is_nickname_forbidden(user_id):
                return jsonify({'error': 'Заборонений нікнейм'}), 400

            # Sanitize message (basic)
            if len(message) > 1000:
                message = message[:1000]

            # Create message object
            kyiv_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(kyiv_tz)

            # Check if sender is a moderator
            sender_is_moderator = is_chat_moderator(device_id)

            new_message = {
                'id': str(uuid.uuid4()),
                'userId': user_id,
                'deviceId': device_id,  # Store deviceId for isMe detection after nickname change
                'message': message,
                'timestamp': now.timestamp(),
                'time': now.strftime('%H:%M'),
                'date': now.strftime('%d.%m.%Y'),
                'isModerator': sender_is_moderator  # Show moderator badge to other users
            }

            # Add reply reference if provided
            if reply_to:
                messages = load_chat_messages()
                # Find the original message being replied to
                original_msg = next((m for m in messages if m.get('id') == reply_to), None)
                if original_msg:
                    new_message['replyTo'] = {
                        'id': original_msg.get('id'),
                        'userId': original_msg.get('userId'),
                        'message': original_msg.get('message', '')[:100]  # Truncate preview
                    }

            # Load, append, save
            messages = load_chat_messages()
            messages.append(new_message)
            save_chat_messages(messages)

            # Record message for rate limiting
            _chat_rate_limiter.record_message(device_id)

            # Broadcast new message via SSE
            broadcast_chat_event('new_message', new_message)
        
            # Clear typing indicator for this user
            CHAT_TYPING_USERS.pop(device_id, None)

            # Trigger git sync for persistence
            try:
                maybe_git_autocommit()
            except Exception as git_err:
                log.warning(f"Git autocommit failed for chat: {git_err}")

            log.info(f"Chat message from {user_id[:20]}: {message[:50]}...")

            return jsonify({
                'success': True,
                'message': new_message
            })
        except Exception as e:
            log.error(f"Error sending chat message: {e}")
            return jsonify({'error': str(e)}), 500

    # Moderator secret for message deletion
    MODERATOR_SECRET = '99446626'

    # List of moderator device IDs
    CHAT_MODERATORS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_moderators.json') if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR) else 'chat_moderators.json'

    def load_chat_moderators():
        """Load list of moderator device IDs."""
        try:
            if os.path.exists(CHAT_MODERATORS_FILE):
                with open(CHAT_MODERATORS_FILE, encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.error(f"Error loading chat moderators: {e}")
        return []

    def save_chat_moderators(moderators):
        """Save list of moderator device IDs."""
        try:
            with open(CHAT_MODERATORS_FILE, 'w', encoding='utf-8') as f:
                json.dump(moderators, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Error saving chat moderators: {e}")

    def is_chat_moderator(device_id):
        """Check if device is a chat moderator.
    
        Also checks JWT token claim if available.
        """
        if not device_id:
            return False
    
        # Check JWT token claim first (more secure)
        try:
            user = get_current_user()
            if user and user.get('is_moderator'):
                return True
        except Exception:
            pass
    
        # Fallback to device_id list
        moderators = load_chat_moderators()
        return device_id in moderators

    @app.route('/api/chat/message/<message_id>', methods=['DELETE'])
    def delete_chat_message(message_id):
        """Delete a chat message (moderator or owner only)."""
        try:
            data = request.get_json() or {}
            device_id = data.get('deviceId', '')

            messages = load_chat_messages()

            # Find the message
            message_to_delete = next((m for m in messages if m.get('id') == message_id), None)

            if not message_to_delete:
                return jsonify({'error': 'Повідомлення не знайдено'}), 404

            # SERVER-SIDE moderator check - don't trust client isModerator flag!
            is_actual_moderator = is_chat_moderator(device_id)
        
            # Check permissions - either moderator or message owner
            if is_actual_moderator:
                # Moderators can delete any message
                pass
            elif device_id:
                # Regular users can only delete their own messages
                nicknames = load_chat_nicknames()
                message_user = message_to_delete.get('userId')
                user_device = nicknames.get(message_user)
                if user_device != device_id:
                    return jsonify({'error': 'Немає прав для видалення'}), 403
            else:
                return jsonify({'error': 'Немає прав для видалення'}), 403

            # Remove the message
            messages = [m for m in messages if m.get('id') != message_id]
            save_chat_messages(messages)
        
            # Broadcast message deletion via SSE
            broadcast_chat_event('delete_message', {'messageId': message_id})

            log.info(f"Chat message {message_id} deleted by {'moderator' if is_actual_moderator else device_id[:20]}")

            return jsonify({
                'success': True,
                'message': 'Повідомлення видалено'
            })
        except Exception as e:
            log.error(f"Error deleting chat message: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/ban-user', methods=['POST'])
    def ban_chat_user():
        """Ban a user from chat (moderator only)."""
        try:
            data = request.get_json() or {}
            target_nickname = data.get('nickname', '')
            device_id = data.get('deviceId', '')
            reason = data.get('reason', 'Порушення правил чату')

            # SERVER-SIDE moderator check - don't trust client isModerator flag!
            if not is_chat_moderator(device_id):
                log.warning(f"Unauthorized ban attempt from device: {device_id[:20] if device_id else 'unknown'}...")
                return jsonify({'error': 'Тільки модератори можуть блокувати'}), 403

            if not target_nickname:
                return jsonify({'error': 'Вкажіть нікнейм'}), 400

            # Find device ID for this nickname
            nicknames = load_chat_nicknames()
            target_device_id = nicknames.get(target_nickname)

            if not target_device_id:
                return jsonify({'error': 'Користувача не знайдено'}), 404

            # Add to banned list
            banned = load_banned_users()
            kyiv_tz = pytz.timezone('Europe/Kiev')
            now = datetime.now(kyiv_tz)

            banned[target_device_id] = {
                'nickname': target_nickname,
                'reason': reason,
                'bannedAt': now.isoformat(),
                'bannedAtTimestamp': now.timestamp()
            }
            save_banned_users(banned)

            log.info(f"User banned: {target_nickname} (device: {target_device_id[:20]}...) - Reason: {reason}")

            return jsonify({
                'success': True,
                'message': f'Користувач {target_nickname} заблокований'
            })
        except Exception as e:
            log.error(f"Error banning user: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/unban-user', methods=['POST'])
    def unban_chat_user():
        """Unban a user from chat (moderator only)."""
        try:
            data = request.get_json() or {}
            target_nickname = data.get('nickname', '')
            device_id = data.get('deviceId', '')

            # SERVER-SIDE moderator check - don't trust client isModerator flag!
            if not is_chat_moderator(device_id):
                log.warning(f"Unauthorized unban attempt from device: {device_id[:20] if device_id else 'unknown'}...")
                return jsonify({'error': 'Тільки модератори можуть розблоковувати'}), 403

            if not target_nickname:
                return jsonify({'error': 'Вкажіть нікнейм'}), 400

            # Find device ID for this nickname
            nicknames = load_chat_nicknames()
            target_device_id = nicknames.get(target_nickname)

            # Remove from banned list (check both by device and nickname)
            banned = load_banned_users()
            removed = False

            if target_device_id and target_device_id in banned:
                del banned[target_device_id]
                removed = True

            # Also check by nickname in case device ID changed
            for device_id, info in list(banned.items()):
                if info.get('nickname') == target_nickname:
                    del banned[device_id]
                    removed = True

            if not removed:
                return jsonify({'error': 'Користувач не заблокований'}), 404

            save_banned_users(banned)
            log.info(f"User unbanned: {target_nickname}")

            return jsonify({
                'success': True,
                'message': f'Користувач {target_nickname} розблокований'
            })
        except Exception as e:
            log.error(f"Error unbanning user: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/check-ban', methods=['POST'])
    def check_user_ban():
        """Check if current user is banned."""
        try:
            data = request.get_json() or {}
            device_id = data.get('deviceId', '')

            if not device_id:
                return jsonify({'banned': False})

            banned = load_banned_users()
            ban_info = banned.get(device_id)

            if ban_info:
                return jsonify({
                    'banned': True,
                    'reason': ban_info.get('reason', 'Порушення правил'),
                    'bannedAt': ban_info.get('bannedAt', '')
                })

            return jsonify({'banned': False})
        except Exception as e:
            log.error(f"Error checking ban: {e}")
            return jsonify({'banned': False})

    @app.route('/api/chat/banned-users', methods=['GET'])
    def get_banned_users():
        """Get list of banned users (moderator only)."""
        try:
            # SERVER-SIDE moderator check
            device_id = request.args.get('deviceId', '')
            if not is_chat_moderator(device_id):
                return jsonify({'error': 'Доступ заборонено'}), 403

            banned = load_banned_users()
            users = []
            for device_id, info in banned.items():
                users.append({
                    'deviceId': device_id[:20] + '...',
                    'nickname': info.get('nickname', 'Unknown'),
                    'reason': info.get('reason', ''),
                    'bannedAt': info.get('bannedAt', '')
                })

            return jsonify({'users': users, 'count': len(users)})
        except Exception as e:
            log.error(f"Error getting banned users: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/add-moderator', methods=['POST'])
    def add_chat_moderator():
        """Add a device as chat moderator (requires admin secret)."""
        try:
            data = request.get_json() or {}
            secret = data.get('secret', '')
            device_id = data.get('deviceId', '')

            if secret != MODERATOR_SECRET:
                return jsonify({'error': 'Невірний секрет'}), 403

            if not device_id:
                return jsonify({'error': 'deviceId обовʼязковий'}), 400

            moderators = load_chat_moderators()
            if device_id not in moderators:
                moderators.append(device_id)
                save_chat_moderators(moderators)
                log.info(f"Added chat moderator: {device_id[:20]}...")

            return jsonify({'success': True, 'message': 'Модератора додано'})
        except Exception as e:
            log.error(f"Error adding moderator: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/remove-moderator', methods=['POST'])
    def remove_chat_moderator():
        """Remove a device from chat moderators (requires admin secret)."""
        try:
            data = request.get_json() or {}
            secret = data.get('secret', '')
            device_id = data.get('deviceId', '')

            if secret != MODERATOR_SECRET:
                return jsonify({'error': 'Невірний секрет'}), 403

            if not device_id:
                return jsonify({'error': 'deviceId обовʼязковий'}), 400

            moderators = load_chat_moderators()
            if device_id in moderators:
                moderators.remove(device_id)
                save_chat_moderators(moderators)
                log.info(f"Removed chat moderator: {device_id[:20]}...")

            return jsonify({'success': True, 'message': 'Модератора видалено'})
        except Exception as e:
            log.error(f"Error removing moderator: {e}")
            return jsonify({'error': str(e)}), 500


    @app.route('/api/chat/user-profile', methods=['POST'])
    def get_chat_user_profile():
        """Get user profile info - basic info for all, detailed for moderators."""
        try:
            data = request.get_json() or {}
            requester_device_id = data.get('requesterDeviceId', '')
            target_device_id = data.get('targetDeviceId', '')
            target_user_id = data.get('targetUserId', '')

            log.info(f"Profile request: requester={requester_device_id[:20] if requester_device_id else 'none'}..., target_user={target_user_id}")

            # Check if requester is moderator
            is_requester_mod = is_chat_moderator(requester_device_id)
            log.info(f"Requester is moderator: {is_requester_mod}")

            # Find device_id from userId if not provided
            if not target_device_id and target_user_id:
                nicknames = load_chat_nicknames()
                target_device_id = nicknames.get(target_user_id, '')
                log.info(f"Lookup nickname '{target_user_id}' -> device: {target_device_id[:20] if target_device_id else 'NOT_FOUND'}...")

            # Check if target is moderator
            is_target_mod = is_chat_moderator(target_device_id) if target_device_id else False

            # Check if target is banned
            is_banned = is_user_banned(target_device_id) if target_device_id else False

            # Basic response for all users
            response_data = {
                'userId': target_user_id,
                'isModerator': is_target_mod,
                'isBanned': is_banned,
            }

            # If requester is moderator - show more details
            if is_requester_mod and target_device_id:
                # Load device data from device_store
                devices = device_store._load()
                device_data = devices.get(target_device_id, {})

                # Get regions from device data
                regions = device_data.get('regions', [])
                log.info(f"Found regions for device: {regions}")

                response_data['deviceId'] = target_device_id[:20] + '...' if len(target_device_id) > 20 else target_device_id
                response_data['regions'] = regions
                response_data['lastSeen'] = device_data.get('last_seen', '')
            else:
                # For regular users - only basic info
                response_data['regions'] = []
                response_data['message'] = 'Детальна інформація доступна тільки модераторам'

            return jsonify(response_data)
        except Exception as e:
            log.error(f"Error getting user profile: {e}")
            return jsonify({'error': str(e)}), 500


    # ============= PUSH NOTIFICATIONS FOR ALARMS =============

    # Store previous alarm state to detect changes
    _previous_alarms = {}

    def check_alarm_changes():
        """Background task to check for alarm changes and send notifications."""
        global _previous_alarms

        if not firebase_initialized:
            return

        try:

            # Fetch current alarms
            response = http_requests.get(
                f'{ALARM_API_BASE}/alerts',
                headers={'Authorization': ALARM_API_KEY},
                timeout=8
            )

            if not response.ok:
                return

            data = response.json()
            current_alarms = {}

            # Build current alarm state by region name
            for region in data:
                region_name = region.get('regionName', '')
                active_alerts = region.get('activeAlerts', [])
                if active_alerts:
                    current_alarms[region_name] = active_alerts

            # Compare with previous state
            if _previous_alarms:
                # Check for new alarms (started)
                for region, alerts in current_alarms.items():
                    if region not in _previous_alarms:
                        # New alarm started
                        _send_alarm_notification(region, alerts, 'started')

                # Check for ended alarms
                for region, alerts in _previous_alarms.items():
                    if region not in current_alarms:
                        # Alarm ended
                        _send_alarm_notification(region, alerts, 'ended')

            # Update previous state
            _previous_alarms = current_alarms

        except Exception as e:
            log.error(f"Error checking alarm changes: {e}")

    def _send_alarm_notification(region, alerts, status):
        """Send push notification for alarm change."""
        try:
            from firebase_admin import messaging

            # Get alert types
            alert_types = [alert.get('type', '') for alert in alerts]

            # Determine criticality
            critical_types = ['Повітряна тривога', 'Ракетна небезпека', 'Хімічна загроза']
            is_critical = any(t in critical_types for t in alert_types)

            # Build notification message
            if status == 'started':
                emoji = '🚨' if is_critical else '⚠️'
                title = f'{emoji} Повітряна тривога!'
                body = f'{region}: {", ".join(alert_types)}'
            else:
                emoji = '✅'
                title = f'{emoji} Відбій тривоги'
                body = f'{region}: тривога закінчена'

            # Get devices subscribed to this region
            devices = device_store.get_devices_for_region(region)

            if not devices:
                return

            # Send to all subscribed devices
            messages = []
            for device in devices:
                if device.get('token'):
                    messages.append(messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body,
                        ),
                        data={
                            'type': 'rocket' if is_critical else 'drone',
                            'region': region,
                            'status': status,
                        },
                        token=device['token'],
                        android=messaging.AndroidConfig(
                            priority='high' if is_critical else 'normal',
                            notification=messaging.AndroidNotification(
                                channel_id='critical_alerts' if is_critical else 'normal_alerts',
                                sound='default',
                            ),
                        ),
                        apns=messaging.APNSConfig(
                            headers={
                                'apns-priority': '10',
                                'apns-push-type': 'alert',
                                'apns-expiration': '0',
                            },
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    alert=messaging.ApsAlert(title=title, body=body),
                                    sound='default',
                                    badge=1,
                                    content_available=True,
                                    mutable_content=True,
                                ),
                            ),
                        ),
                    ))

            if messages:
                # Send batch
                response = messaging.send_all(messages)
                log.info(f"Sent {response.success_count} notifications for {region} ({status})")

        except Exception as e:
            log.error(f"Error sending alarm notification: {e}")

    # Background thread for monitoring alarms
    def _alarm_monitor_thread():
        """Background thread that checks for alarm changes every 30 seconds."""
        gc_counter = 0
        while True:
            try:
                check_alarm_changes()

                # MEMORY OPTIMIZATION: Force garbage collection every 5 minutes
                gc_counter += 1
                if gc_counter >= 10:  # 10 * 30 sec = 5 minutes
                    gc.collect()
                    gc_counter = 0

            except Exception as e:
                log.error(f"Alarm monitor thread error: {e}")
            time.sleep(30)  # Check every 30 seconds

    # Start alarm monitoring thread
    # DISABLED: Using monitor_alarms() instead which has better deduplication logic
    # _alarm_monitor = threading.Thread(target=_alarm_monitor_thread, daemon=True)
    # _alarm_monitor.start()
    log.info("Old alarm monitoring thread DISABLED - using monitor_alarms() instead")


    @app.route('/api/stats')
    def get_alarm_stats():
        """Get alarm statistics for a region from persistent database."""
        try:
            region = request.args.get('region', 'Дніпропетровська')
        
            # Get stats from persistent SQLite database
            stats = get_alarm_stats_from_db(region)
        
            # Average alarm duration (rough estimate)
            avg_duration = 25  # Default 25 min

            return jsonify({
                'region': region,
                'today_alarms': stats['today_alarms'],
                'week_alarms': stats['week_alarms'],
                'month_alarms': stats['month_alarms'],
                'avg_duration_min': avg_duration,
            })
        except Exception as e:
            log.error(f"Error getting stats: {e}")
            return jsonify({
                'today_alarms': 0,
                'week_alarms': 0,
                'month_alarms': 0,
                'avg_duration_min': 0,
            })

    # =============================================================================
    # DEBUG: Route Patterns Viewer
    # =============================================================================
    @app.route('/api/ai/route-patterns')
    def api_route_patterns():
        """View AI learned route patterns"""
        try:
            patterns = _load_route_patterns()
            return jsonify({
                'status': 'ok',
                'file': ROUTE_PATTERNS_FILE,
                'patterns_count': len(patterns.get('patterns', {})),
                'historical_routes_count': len(patterns.get('historical_routes', [])),
                'ai_corrections_count': len(patterns.get('ai_corrections', [])),
                'last_updated': patterns.get('last_updated'),
                'data': patterns
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


