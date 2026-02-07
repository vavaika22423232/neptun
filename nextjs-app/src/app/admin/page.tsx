'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';

const MapEditor = dynamic(() => import('@/components/admin/MapEditor'), { ssr: false });

type Tab = 'overview' | 'markers' | 'messages' | 'users' | 'settings' | 'corrections';

function formatKyivTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('uk-UA', {
      timeZone: 'Europe/Kyiv',
      hour: '2-digit', minute: '2-digit',
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  } catch { return iso; }
}

interface Stats {
  totalMessages: number;
  markersCount: number;
  hiddenCount: number;
  blockedCount: number;
  pendingGeoCount: number;
  settings: { monitorPeriod: number; ttlEnabled: boolean };
}

interface MarkerRecord {
  id: string;
  lat: number;
  lng: number;
  threat_type: string;
  place: string;
  text: string;
  date: string;
  manual?: boolean;
  rotation?: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

interface HiddenMarker { lat: string; lng: string; text: string; source: string; key: string; }

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(path, { cache: 'no-store', ...opts });
  if (res.status === 401) throw new Error('UNAUTHORIZED');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [markers, setMarkers] = useState<MarkerRecord[]>([]);
  const [hidden, setHidden] = useState<HiddenMarker[]>([]);
  const [rawMsgs, setRawMsgs] = useState<MarkerRecord[]>([]);
  const [blocked, setBlocked] = useState<string[]>([]);
  const [settings, setSettings] = useState<{ monitorPeriod: number; ttlEnabled: boolean }>({ monitorPeriod: 30, ttlEnabled: true });
  const [corrections, setCorrections] = useState<Array<Record<string, unknown>>>([]);
  const [corrForm, setCorrForm] = useState({ event_id: '', place_name: '', correct_lat: '', correct_lng: '', correct_oblast: '', reason: '' });
  const [notification, setNotification] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const router = useRouter();

  const notify = useCallback((text: string, type: 'success' | 'error' = 'success') => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 3000);
  }, []);

  const handleAuthError = useCallback(() => {
    router.push('/admin/login');
  }, [router]);

  // ── Loaders ──

  const loadStats = useCallback(async () => {
    try {
      const data = await api<Stats>('/api/admin/stats');
      setStats(data);
      setSettings(data.settings);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  const loadMarkers = useCallback(async () => {
    try {
      const data = await api<{ markers: MarkerRecord[] }>('/api/admin/markers');
      setMarkers(data.markers || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  const loadHidden = useCallback(async () => {
    try {
      const data = await api<{ hidden: HiddenMarker[] }>('/api/admin/hidden');
      setHidden(data.hidden || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  const loadRawMsgs = useCallback(async () => {
    try {
      const data = await api<{ raw_msgs: MarkerRecord[] }>('/api/admin/messages/raw');
      setRawMsgs(data.raw_msgs || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  const loadBlocked = useCallback(async () => {
    try {
      const data = await api<{ blocked: string[] }>('/api/admin/users');
      setBlocked(data.blocked || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  const loadCorrections = useCallback(async () => {
    try {
      const data = await api<{ corrections: Array<Record<string, unknown>>; total: number }>('/api/admin/corrections');
      setCorrections(data.corrections || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  useEffect(() => {
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (tab === 'markers') { loadMarkers(); loadHidden(); }
    if (tab === 'messages') loadRawMsgs();
    if (tab === 'users') loadBlocked();
    if (tab === 'settings') loadStats();
    if (tab === 'corrections') loadCorrections();
  }, [tab, loadMarkers, loadHidden, loadRawMsgs, loadBlocked, loadStats, loadCorrections]);

  // ── Actions ──

  const handleLogout = async () => {
    await fetch('/api/admin/auth/logout', { method: 'POST' });
    router.push('/admin/login');
  };

  const deleteMarker = async (id: string) => {
    try {
      await api('/api/admin/markers/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
      notify('Метку видалено');
      loadMarkers();
      loadStats();
    } catch { notify('Помилка видалення', 'error'); }
  };

  const hideMarker = async (m: MarkerRecord) => {
    try {
      await api('/api/admin/hidden/hide', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lat: m.lat, lng: m.lng, text: m.text, source: m.manual ? 'manual' : 'auto' }) });
      notify('Метку приховано');
      loadMarkers();
      loadHidden();
      loadStats();
    } catch { notify('Помилка', 'error'); }
  };

  const unhideMarker = async (key: string) => {
    try {
      await api('/api/admin/hidden/unhide', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
      notify('Метку відновлено');
      loadHidden();
      loadStats();
    } catch { notify('Помилка', 'error'); }
  };

  const blockUser = async (id: string) => {
    try {
      await api('/api/admin/users/block', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
      notify('Користувача заблоковано');
      loadBlocked();
      loadStats();
    } catch { notify('Помилка', 'error'); }
  };

  const unblockUser = async (id: string) => {
    try {
      await api('/api/admin/users/unblock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
      notify('Користувача розблоковано');
      loadBlocked();
      loadStats();
    } catch { notify('Помилка', 'error'); }
  };

  const saveMonitorPeriod = async (value: number) => {
    try {
      await api('/api/admin/settings/monitor-period', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }) });
      setSettings(s => ({ ...s, monitorPeriod: value }));
      notify('Збережено');
    } catch { notify('Помилка', 'error'); }
  };

  const toggleTTL = async () => {
    try {
      const newVal = !settings.ttlEnabled;
      await api('/api/admin/settings/ttl', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: newVal }) });
      setSettings(s => ({ ...s, ttlEnabled: newVal }));
      notify(`TTL ${newVal ? 'увімкнено' : 'вимкнено'}`);
    } catch { notify('Помилка', 'error'); }
  };

  // ── Add Marker Form state ──
  const [addForm, setAddForm] = useState({ lat: '', lng: '', text: '', place: '', threat_type: 'shahed' });

  const addMarker = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api('/api/admin/markers/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: parseFloat(addForm.lat),
          lng: parseFloat(addForm.lng),
          text: addForm.text,
          place: addForm.place,
          threat_type: addForm.threat_type,
        }),
      });
      notify('Метку додано');
      setAddForm({ lat: '', lng: '', text: '', place: '', threat_type: 'shahed' });
      loadMarkers();
      loadStats();
    } catch { notify('Помилка додавання', 'error'); }
  };

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Огляд', icon: 'dashboard' },
    { id: 'markers', label: 'Мітки', icon: 'place' },
    { id: 'messages', label: 'Повідомлення', icon: 'message' },
    { id: 'users', label: 'Користувачі', icon: 'people' },
    { id: 'settings', label: 'Налаштування', icon: 'settings' },
    { id: 'corrections', label: 'Корекції', icon: 'edit_location' },
  ];

  const threatTypes = ['shahed', 'raketa', 'avia', 'pvo', 'vibuh', 'alarm', 'alarm_cancel', 'obstril', 'fpv', 'pusk', 'kab', 'rszv', 'rozved', 'manual'];

  return (
    <div className="min-h-screen bg-[#0a0e17] text-[#e2e2e6]">
      {/* Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 z-[9999] px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg animate-[fadeIn_0.2s_ease] ${notification.type === 'success' ? 'bg-[#69f0ae]/15 text-[#69f0ae] border border-[#69f0ae]/20' : 'bg-red-400/15 text-red-400 border border-red-400/20'}`}>
          {notification.text}
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#0e1218]/90 backdrop-blur-xl border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold tracking-[4px] text-white/80">NEPTUN</span>
          <span className="text-xs text-[#80d8ff]/50 bg-[#80d8ff]/10 px-2 py-0.5 rounded-lg">Admin</span>
        </div>
        <button onClick={handleLogout} className="text-xs text-white/40 hover:text-red-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-400/10">
          <span className="material-icons text-[16px] mr-1 align-middle">logout</span>
          Вийти
        </button>
      </header>

      <div className="flex h-[calc(100vh-52px)]">
        {/* Sidebar */}
        <nav className="w-56 bg-[#0e1420] border-r border-white/5 p-3 flex flex-col gap-1 max-md:hidden overflow-y-auto shrink-0">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all text-left w-full ${tab === t.id ? 'bg-[#80d8ff]/12 text-[#80d8ff]' : 'text-white/50 hover:bg-white/5 hover:text-white/70'}`}
            >
              <span className="material-icons text-[20px]">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>

        {/* Mobile tabs */}
        <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#0e1420] border-t border-white/5 flex justify-around p-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex flex-col items-center gap-0.5 px-2 py-2 rounded-xl text-[10px] min-w-[56px] transition-all ${tab === t.id ? 'text-[#80d8ff]' : 'text-white/40'}`}
            >
              <span className="material-icons text-[20px]">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <main className="flex-1 p-4 md:p-6 max-md:pb-20 overflow-y-auto">

          {/* ── OVERVIEW ── */}
          {tab === 'overview' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white/90">Огляд системи</h2>
              {stats ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Повідомлень', value: stats.totalMessages, icon: 'message', color: '#80d8ff' },
                    { label: 'Міток на карті', value: stats.markersCount, icon: 'place', color: '#69f0ae' },
                    { label: 'Приховано', value: stats.hiddenCount, icon: 'visibility_off', color: '#ffab40' },
                    { label: 'Заблоковано', value: stats.blockedCount, icon: 'block', color: '#ff5252' },
                    { label: 'Pending Geo', value: stats.pendingGeoCount, icon: 'pending', color: '#b388ff' },
                    { label: 'Монітор (хв)', value: stats.settings.monitorPeriod, icon: 'timer', color: '#80d8ff' },
                    { label: 'TTL Система', value: stats.settings.ttlEnabled ? 'Увімк.' : 'Вимк.', icon: 'schedule', color: stats.settings.ttlEnabled ? '#69f0ae' : '#ff5252' },
                  ].map((s, i) => (
                    <div key={i} className="bg-[#1a2030] rounded-2xl p-4 border border-white/5">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="material-icons text-[18px]" style={{ color: s.color }}>{s.icon}</span>
                        <span className="text-xs text-white/40">{s.label}</span>
                      </div>
                      <div className="text-2xl font-semibold text-white/90">{s.value}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-white/30 animate-pulse">Завантаження...</div>
              )}
              <button onClick={loadStats} className="text-xs text-[#80d8ff]/60 hover:text-[#80d8ff] transition-colors">
                <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
              </button>
            </div>
          )}

          {/* ── MARKERS ── */}
          {tab === 'markers' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white/90">Мітки ({markers.length})</h2>
                <button onClick={() => { loadMarkers(); loadHidden(); }} className="text-xs text-[#80d8ff]/60 hover:text-[#80d8ff] transition-colors">
                  <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
                </button>
              </div>

              {/* Add marker form */}
              <form onSubmit={addMarker} className="bg-[#1a2030] rounded-2xl p-4 border border-white/5 space-y-3">
                <h3 className="text-sm font-medium text-white/70 mb-2">Додати мітку</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <input placeholder="Lat" value={addForm.lat} onChange={e => setAddForm(f => ({ ...f, lat: e.target.value }))} className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#80d8ff]/30" required />
                  <input placeholder="Lng" value={addForm.lng} onChange={e => setAddForm(f => ({ ...f, lng: e.target.value }))} className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#80d8ff]/30" required />
                  <input placeholder="Місце" value={addForm.place} onChange={e => setAddForm(f => ({ ...f, place: e.target.value }))} className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#80d8ff]/30" />
                  <select value={addForm.threat_type} onChange={e => setAddForm(f => ({ ...f, threat_type: e.target.value }))} className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30">
                    {threatTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <input placeholder="Текст повідомлення" value={addForm.text} onChange={e => setAddForm(f => ({ ...f, text: e.target.value }))} className="w-full bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#80d8ff]/30" required />
                <button type="submit" className="bg-[#80d8ff]/15 hover:bg-[#80d8ff]/25 text-[#80d8ff] text-sm px-4 py-2 rounded-xl transition-all border border-[#80d8ff]/10">
                  <span className="material-icons text-[14px] mr-1 align-middle">add</span>Додати
                </button>
              </form>

              {/* Markers table */}
              <div className="bg-[#1a2030] rounded-2xl border border-white/5 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/5 text-white/40 text-xs">
                        <th className="text-left px-4 py-3">Час</th>
                        <th className="text-left px-4 py-3">Тип</th>
                        <th className="text-left px-4 py-3">Місце</th>
                        <th className="text-left px-4 py-3 max-w-[200px]">Текст</th>
                        <th className="text-left px-4 py-3">Коорд.</th>
                        <th className="text-right px-4 py-3">Дії</th>
                      </tr>
                    </thead>
                    <tbody>
                      {markers.slice(0, 50).map(m => (
                        <tr key={m.id} className="border-b border-white/3 hover:bg-white/3 transition-colors">
                          <td className="px-4 py-2.5 text-xs text-white/40 whitespace-nowrap">{formatKyivTime(m.date)}</td>
                          <td className="px-4 py-2.5">
                            <span className={`text-xs px-2 py-0.5 rounded-lg ${m.threat_type === 'shahed' ? 'bg-[#80d8ff]/10 text-[#80d8ff]' : m.threat_type === 'raketa' ? 'bg-red-400/10 text-red-400' : 'bg-[#ffab40]/10 text-[#ffab40]'}`}>
                              {m.threat_type}{m.manual ? ' (ручна)' : ''}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-white/70 text-xs">{m.place}</td>
                          <td className="px-4 py-2.5 text-white/50 text-xs max-w-[200px] truncate">{m.text}</td>
                          <td className="px-4 py-2.5 text-white/30 text-[11px] font-mono">{m.lat?.toFixed(3)}, {m.lng?.toFixed(3)}</td>
                          <td className="px-4 py-2.5 text-right">
                            <div className="flex gap-1 justify-end">
                              <button onClick={() => hideMarker(m)} className="text-[#ffab40]/60 hover:text-[#ffab40] p-1 rounded-lg hover:bg-[#ffab40]/10 transition-all" title="Приховати">
                                <span className="material-icons text-[16px]">visibility_off</span>
                              </button>
                              {m.manual && (
                                <button onClick={() => deleteMarker(m.id)} className="text-red-400/60 hover:text-red-400 p-1 rounded-lg hover:bg-red-400/10 transition-all" title="Видалити">
                                  <span className="material-icons text-[16px]">delete</span>
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Map editor */}
              <MapEditor
                markers={markers}
                onAddMarker={(lat, lng) => {
                  setAddForm(f => ({ ...f, lat: lat.toFixed(5), lng: lng.toFixed(5) }));
                }}
                onMoveMarker={async (id, lat, lng) => {
                  try {
                    await api('/api/admin/markers/update', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ id, lat, lng }),
                    });
                    notify('Мітку переміщено');
                    loadMarkers();
                  } catch { notify('Помилка', 'error'); }
                }}
                onSelectMarker={(m) => {
                  setAddForm({ lat: String(m.lat), lng: String(m.lng), text: m.text, place: m.place, threat_type: m.threat_type });
                }}
              />

              {/* Hidden markers */}
              <div className="bg-[#1a2030] rounded-2xl p-4 border border-white/5">
                <h3 className="text-sm font-medium text-white/70 mb-3">Приховані мітки ({hidden.length})</h3>
                {hidden.length === 0 ? (
                  <div className="text-white/30 text-sm">Немає прихованих міток</div>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {hidden.map((h, i) => (
                      <div key={i} className="flex items-center justify-between bg-[#0e1420] rounded-xl px-3 py-2 text-xs">
                        <span className="text-white/40 truncate flex-1 mr-2">{h.text || `${h.lat}, ${h.lng}`}</span>
                        <button onClick={() => unhideMarker(h.key)} className="text-[#69f0ae]/60 hover:text-[#69f0ae] text-xs px-2 py-1 rounded-lg hover:bg-[#69f0ae]/10 transition-all whitespace-nowrap">
                          <span className="material-icons text-[14px] mr-0.5 align-middle">visibility</span>Показати
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── MESSAGES ── */}
          {tab === 'messages' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white/90">Повідомлення (pending geo: {rawMsgs.length})</h2>
                <button onClick={loadRawMsgs} className="text-xs text-[#80d8ff]/60 hover:text-[#80d8ff] transition-colors">
                  <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
                </button>
              </div>
              <div className="bg-[#1a2030] rounded-2xl border border-white/5 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/5 text-white/40 text-xs">
                        <th className="text-left px-4 py-3">Час</th>
                        <th className="text-left px-4 py-3">Канал</th>
                        <th className="text-left px-4 py-3">Текст</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rawMsgs.length === 0 && (
                        <tr><td colSpan={3} className="px-4 py-6 text-center text-white/30">Немає повідомлень з pending geo</td></tr>
                      )}
                      {rawMsgs.map((m, i) => (
                        <tr key={i} className="border-b border-white/3 hover:bg-white/3 transition-colors">
                          <td className="px-4 py-2.5 text-xs text-white/40 whitespace-nowrap">{formatKyivTime(m.date)}</td>
                          <td className="px-4 py-2.5 text-xs text-[#80d8ff]/60">{m.channel || m.source}</td>
                          <td className="px-4 py-2.5 text-white/60 text-xs">{(m.text || '').slice(0, 120)}{(m.text || '').length > 120 ? '...' : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── USERS ── */}
          {tab === 'users' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white/90">Заблоковані користувачі ({blocked.length})</h2>

              {/* Block form */}
              <div className="bg-[#1a2030] rounded-2xl p-4 border border-white/5">
                <h3 className="text-sm font-medium text-white/70 mb-2">Заблокувати користувача</h3>
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  const input = (e.target as HTMLFormElement).elements.namedItem('blockId') as HTMLInputElement;
                  if (input.value.trim()) {
                    await blockUser(input.value.trim());
                    input.value = '';
                  }
                }} className="flex gap-2">
                  <input name="blockId" placeholder="User ID" className="flex-1 bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#80d8ff]/30" />
                  <button type="submit" className="bg-red-400/15 hover:bg-red-400/25 text-red-400 text-sm px-4 py-2 rounded-xl transition-all border border-red-400/10">
                    <span className="material-icons text-[14px] mr-1 align-middle">block</span>Блокувати
                  </button>
                </form>
              </div>

              {/* Blocked list */}
              <div className="bg-[#1a2030] rounded-2xl p-4 border border-white/5">
                {blocked.length === 0 ? (
                  <div className="text-white/30 text-sm">Немає заблокованих</div>
                ) : (
                  <div className="space-y-2">
                    {blocked.map((id, i) => (
                      <div key={i} className="flex items-center justify-between bg-[#0e1420] rounded-xl px-3 py-2 text-xs">
                        <span className="text-white/50 font-mono">{id}</span>
                        <button onClick={() => unblockUser(id)} className="text-[#69f0ae]/60 hover:text-[#69f0ae] text-xs px-2 py-1 rounded-lg hover:bg-[#69f0ae]/10 transition-all">
                          <span className="material-icons text-[14px] mr-0.5 align-middle">lock_open</span>Розблокувати
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── SETTINGS ── */}
          {tab === 'settings' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white/90">Налаштування</h2>

              {/* Monitor period */}
              <div className="bg-[#1a2030] rounded-2xl p-4 border border-white/5 space-y-3">
                <h3 className="text-sm font-medium text-white/70">Період моніторингу (хвилини)</h3>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min={1}
                    max={360}
                    value={settings.monitorPeriod}
                    onChange={e => setSettings(s => ({ ...s, monitorPeriod: parseInt(e.target.value) || 30 }))}
                    className="w-24 bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  />
                  <button onClick={() => saveMonitorPeriod(settings.monitorPeriod)} className="bg-[#80d8ff]/15 hover:bg-[#80d8ff]/25 text-[#80d8ff] text-sm px-4 py-2 rounded-xl transition-all border border-[#80d8ff]/10">
                    Зберегти
                  </button>
                </div>
              </div>

              {/* TTL toggle */}
              <div className="bg-[#1a2030] rounded-2xl p-4 border border-white/5 space-y-3">
                <h3 className="text-sm font-medium text-white/70">TTL Система (автоматичне видалення старих міток)</h3>
                <button onClick={toggleTTL} className={`px-4 py-2 rounded-xl text-sm transition-all border ${settings.ttlEnabled ? 'bg-[#69f0ae]/15 text-[#69f0ae] border-[#69f0ae]/20' : 'bg-red-400/15 text-red-400 border-red-400/20'}`}>
                  {settings.ttlEnabled ? 'Увімкнено' : 'Вимкнено'} — натисніть щоб змінити
                </button>
              </div>

              {/* Cache clear */}
              <div className="bg-[#1a2030] rounded-2xl p-4 border border-white/5 space-y-3">
                <h3 className="text-sm font-medium text-white/70">Кеш</h3>
                <button onClick={async () => {
                  try {
                    await api('/api/admin/cache/clear', { method: 'POST' });
                    notify('Кеш очищено');
                  } catch { notify('Помилка', 'error'); }
                }} className="bg-[#ffab40]/15 hover:bg-[#ffab40]/25 text-[#ffab40] text-sm px-4 py-2 rounded-xl transition-all border border-[#ffab40]/10">
                  <span className="material-icons text-[14px] mr-1 align-middle">delete_sweep</span>Очистити кеш
                </button>
              </div>
            </div>
          )}

          {tab === 'corrections' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white/90">Корекції гео-резолюції</h2>
              <p className="text-sm text-white/50">Виправляйте помилкові координати — система навчиться автоматично.</p>

              {/* Add correction form */}
              <div className="bg-[#1a2030] rounded-2xl p-5 border border-white/5 space-y-4">
                <h3 className="text-sm font-medium text-white/70 flex items-center gap-2">
                  <span className="material-icons text-[18px] text-[#80d8ff]">add_location</span>
                  Нова корекція
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  <input
                    placeholder="Назва місця"
                    value={corrForm.place_name}
                    onChange={e => setCorrForm(f => ({ ...f, place_name: e.target.value }))}
                    className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  />
                  <input
                    placeholder="Правильна широта"
                    type="number"
                    step="0.0001"
                    value={corrForm.correct_lat}
                    onChange={e => setCorrForm(f => ({ ...f, correct_lat: e.target.value }))}
                    className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  />
                  <input
                    placeholder="Правильна довгота"
                    type="number"
                    step="0.0001"
                    value={corrForm.correct_lng}
                    onChange={e => setCorrForm(f => ({ ...f, correct_lng: e.target.value }))}
                    className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  />
                  <input
                    placeholder="Правильна область"
                    value={corrForm.correct_oblast}
                    onChange={e => setCorrForm(f => ({ ...f, correct_oblast: e.target.value }))}
                    className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  />
                  <select
                    value={corrForm.reason}
                    onChange={e => setCorrForm(f => ({ ...f, reason: e.target.value }))}
                    className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  >
                    <option value="">Причина помилки</option>
                    <option value="duplicate_name">Дублікат назви</option>
                    <option value="wrong_oblast">Хибна область</option>
                    <option value="parser_missed">Парсер не знайшов</option>
                    <option value="geocoder_error">Помилка геокодера</option>
                    <option value="other">Інше</option>
                  </select>
                  <input
                    placeholder="ID події (опц.)"
                    value={corrForm.event_id}
                    onChange={e => setCorrForm(f => ({ ...f, event_id: e.target.value }))}
                    className="bg-[#0e1420] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#80d8ff]/30"
                  />
                </div>
                <button
                  onClick={async () => {
                    if (!corrForm.correct_lat || !corrForm.correct_lng) {
                      notify('Введіть координати', 'error');
                      return;
                    }
                    try {
                      await api('/api/admin/corrections', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(corrForm),
                      });
                      notify('Корекцію збережено');
                      setCorrForm({ event_id: '', place_name: '', correct_lat: '', correct_lng: '', correct_oblast: '', reason: '' });
                      loadCorrections();
                    } catch { notify('Помилка збереження', 'error'); }
                  }}
                  className="bg-[#80d8ff]/15 hover:bg-[#80d8ff]/25 text-[#80d8ff] text-sm px-5 py-2.5 rounded-xl transition-all border border-[#80d8ff]/10"
                >
                  <span className="material-icons text-[14px] mr-1 align-middle">save</span>
                  Зберегти корекцію
                </button>
              </div>

              {/* Corrections list */}
              <div className="bg-[#1a2030] rounded-2xl border border-white/5 overflow-hidden">
                <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
                  <h3 className="text-sm font-medium text-white/70">Останні корекції ({corrections.length})</h3>
                </div>
                {corrections.length === 0 ? (
                  <div className="p-8 text-center text-white/30 text-sm">Корекцій ще немає</div>
                ) : (
                  <div className="max-h-[400px] overflow-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-[#0e1420] sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left text-white/40 font-medium">Місце</th>
                          <th className="px-3 py-2 text-left text-white/40 font-medium">Координати</th>
                          <th className="px-3 py-2 text-left text-white/40 font-medium">Область</th>
                          <th className="px-3 py-2 text-left text-white/40 font-medium">Причина</th>
                          <th className="px-3 py-2 text-left text-white/40 font-medium">Дата</th>
                        </tr>
                      </thead>
                      <tbody>
                        {corrections.map((c, i) => (
                          <tr key={i} className="border-t border-white/5 hover:bg-white/[0.02]">
                            <td className="px-3 py-2 text-white/80">{(c.place_name as string) || '—'}</td>
                            <td className="px-3 py-2 text-white/60 font-mono">
                              {Number(c.correct_lat).toFixed(4)}, {Number(c.correct_lng).toFixed(4)}
                            </td>
                            <td className="px-3 py-2 text-white/60">{(c.correct_oblast as string) || '—'}</td>
                            <td className="px-3 py-2">
                              <span className="inline-block bg-[#80d8ff]/10 text-[#80d8ff] text-[10px] px-2 py-0.5 rounded-full">
                                {(c.reason as string) || 'none'}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-white/40">
                              {c.created_at ? new Date(c.created_at as string).toLocaleDateString('uk-UA') : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* How it works */}
              <div className="bg-[#1a2030] rounded-2xl p-5 border border-white/5 space-y-3">
                <h3 className="text-sm font-medium text-white/70 flex items-center gap-2">
                  <span className="material-icons text-[18px] text-[#ffab40]">info</span>
                  Як працює самонавчання
                </h3>
                <ul className="text-xs text-white/50 space-y-1.5 list-disc list-inside">
                  <li>Корекції зберігаються і аналізуються кожні 6 годин</li>
                  <li>Якщо одне місце виправлено 3+ разів — створюється alias автоматично</li>
                  <li>Якщо геокодер стабільно помиляється — назва потрапляє в blacklist</li>
                  <li>Channel priors оновлюються з кожного нового повідомлення</li>
                  <li>Все це підвищує accuracy з часом без перезапуску системи</li>
                </ul>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
