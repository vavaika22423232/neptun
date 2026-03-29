'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useAdminFeedSSE } from '@/hooks/useDataSSE';

const MapEditor = dynamic(() => import('@/components/admin/MapEditor'), { ssr: false });

type Tab = 'overview' | 'markers' | 'reports' | 'messages' | 'users' | 'settings' | 'corrections' | 'feedback' | 'feed';

interface ChatReport {
  id: string;
  messageId: string;
  reason: string;
  reporterDeviceId: string;
  reporterNickname: string;
  reportedDeviceId?: string;
  reportedNickname?: string;
  originalText: string;
  status: 'PENDING' | 'RESOLVED' | 'REJECTED';
  createdAt: string;
  resolvedAt?: string;
}

interface FeedbackTicket {
  id: string;
  message: string;
  type: string;
  device_id: string;
  device: string;
  app_version: string;
  status: string;
  created_at: string;
  updated_at: string;
  responses: { id: string; message: string; author: string; created_at: string }[];
}

interface FeedEntry {
  _id: string;
  status: 'processed' | 'skipped' | 'dropped' | 'deduped' | 'chain_update' | 'error' | 'retargeted';
  ts: string;
  channel_name?: string;
  msg_text?: string;
  channel_id?: number;
  msg_id?: number;
  reason?: string;
  threat_type?: string;
  entities_count?: number;
  parser?: string;
  place?: string;
  region?: string;
  lat?: number;
  lng?: number;
  speed_kmh?: number;
  course_bearing?: number;
  track_id?: string;
  confidence?: number;
  resolve_status?: string;
  marker_id?: string;
  origin?: string;
}

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
  settings: { monitorPeriod: number; ttlEnabled: boolean; minConfidence: number };
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
  const [tab, setTab] = useState<Tab>('feed');
  const [stats, setStats] = useState<Stats | null>(null);
  const [markers, setMarkers] = useState<MarkerRecord[]>([]);
  const [hidden, setHidden] = useState<HiddenMarker[]>([]);
  const [rawMsgs, setRawMsgs] = useState<MarkerRecord[]>([]);
  const [blocked, setBlocked] = useState<string[]>([]);
  const [settings, setSettings] = useState<{ monitorPeriod: number; ttlEnabled: boolean; minConfidence: number }>({ monitorPeriod: 30, ttlEnabled: true, minConfidence: 0.3 });
  const [corrections, setCorrections] = useState<Array<Record<string, unknown>>>([]);
  const [corrForm, setCorrForm] = useState({ event_id: '', place_name: '', correct_lat: '', correct_lng: '', correct_oblast: '', reason: '' });
  const [feedbackTickets, setFeedbackTickets] = useState<FeedbackTicket[]>([]);
  const [feedbackFilter, setFeedbackFilter] = useState<string>('all');
  const [feedbackTotal, setFeedbackTotal] = useState(0);

  // Chat Moderation Reports
  const [reports, setReports] = useState<ChatReport[]>([]);
  const [reportsFilter, setReportsFilter] = useState<'PENDING' | 'ALL'>('PENDING');
  const [expandedTicket, setExpandedTicket] = useState<string | null>(null);
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [replyingSending, setReplyingSending] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Feed state
  const [feedEntries, setFeedEntries] = useState<FeedEntry[]>([]);
  const [feedFilter, setFeedFilter] = useState<string>('all');
  const [feedPaused, setFeedPaused] = useState(false);
  const [feedExpanded, setFeedExpanded] = useState<string | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);
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

  const loadFeedback = useCallback(async () => {
    try {
      const statusParam = feedbackFilter !== 'all' ? `&status=${feedbackFilter}` : '';
      const data = await api<{ feedback: FeedbackTicket[]; total: number }>(`/api/feedback?limit=100${statusParam}`);
      setFeedbackTickets(data.feedback || []);
      setFeedbackTotal(data.total);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError, feedbackFilter]);

  const loadReports = useCallback(async () => {
    try {
      const data = await api<{ reports: ChatReport[] }>('/api/admin/chat/reports');
      setReports(data.reports || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  const loadFeed = useCallback(async () => {
    try {
      const data = await api<{ entries: FeedEntry[] }>('/api/admin/feed?limit=300');
      setFeedEntries(data.entries || []);
    } catch (e) { if ((e as Error).message === 'UNAUTHORIZED') handleAuthError(); }
  }, [handleAuthError]);

  // SSE real-time feed subscription
  useAdminFeedSSE(useCallback((event: Record<string, unknown>) => {
    if (tab !== 'feed') return;
    if (feedPaused) return;
    setFeedEntries(prev => {
      const entry = event as unknown as FeedEntry;
      const next = [entry, ...prev];
      return next.length > 500 ? next.slice(0, 500) : next;
    });
  }, [tab, feedPaused]));

  useEffect(() => {
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (tab === 'overview') loadStats();
    if (tab === 'markers') { loadMarkers(); loadHidden(); }
    if (tab === 'messages') loadRawMsgs();
    if (tab === 'reports') loadReports();
    if (tab === 'users') loadBlocked();
    if (tab === 'settings') loadStats();
    if (tab === 'corrections') loadCorrections();
    if (tab === 'feedback') loadFeedback();
    if (tab === 'feed') loadFeed();
  }, [tab, loadMarkers, loadHidden, loadRawMsgs, loadBlocked, loadStats, loadCorrections, loadFeedback, loadFeed, loadReports]);

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

  // ── Feedback actions ──

  const respondToFeedback = async (ticketId: string) => {
    const text = replyText[ticketId]?.trim();
    if (!text) return;
    setReplyingSending(ticketId);
    try {
      await api(`/api/feedback/${ticketId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, author: 'admin' }),
      });
      notify('Відповідь надіслано');
      setReplyText(prev => ({ ...prev, [ticketId]: '' }));
      loadFeedback();
    } catch { notify('Помилка', 'error'); }
    setReplyingSending(null);
  };

  const changeFeedbackStatus = async (ticketId: string, status: string) => {
    try {
      await api(`/api/feedback/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      notify('Статус оновлено');
      loadFeedback();
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

  const saveMinConfidence = async (value: number) => {
    try {
      await api('/api/admin/settings/min-confidence', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }) });
      setSettings(s => ({ ...s, minConfidence: value }));
      notify('Поріг впевненості збережено');
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
    { id: 'feed', label: 'Лента', icon: 'rss_feed' },
    { id: 'overview', label: 'Огляд', icon: 'dashboard' },
    { id: 'markers', label: 'Мітки', icon: 'place' },
    { id: 'messages', label: 'Повідомлення', icon: 'message' },
    { id: 'reports', label: 'Скарги (Чат)', icon: 'gavel' },
    { id: 'users', label: 'Користувачі', icon: 'people' },
    { id: 'settings', label: 'Налаштування', icon: 'settings' },
    { id: 'corrections', label: 'Корекції', icon: 'edit_location' },
    { id: 'feedback', label: 'Зворотній зв\'язок', icon: 'feedback' },
  ];

  const threatTypes = ['shahed', 'raketa', 'avia', 'pvo', 'vibuh', 'alarm', 'alarm_cancel', 'obstril', 'fpv', 'pusk', 'kab', 'rszv', 'rozved', 'manual'];

  return (
    <div className="min-h-screen bg-[#050505] text-white/90 selection:bg-[#ff2a5f]/30 font-mono">
      {/* Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 z-[9999] px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg animate-[fadeIn_0.2s_ease] ${notification.type === 'success' ? 'bg-[#5ef5c4]/15 text-[#5ef5c4] border border-[#5ef5c4]/20' : 'bg-red-400/15 text-red-400 border border-red-400/20'}`}>
          {notification.text}
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-50 bg-[var(--surface)]/90 backdrop-blur-xl border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold tracking-[4px] text-white/80">NEPTUN</span>
          <span className="text-xs text-[#ff2a5f]/50 bg-[#ff2a5f]/10 px-2 py-0.5 rounded-lg">Admin</span>
        </div>
        <button onClick={handleLogout} className="text-xs text-white/40 hover:text-red-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-400/10">
          <span className="material-icons text-[16px] mr-1 align-middle">logout</span>
          Вийти
        </button>
      </header>

      <div className="flex h-[calc(100vh-52px)]">
        {/* Sidebar */}
        <nav className="w-56 bg-[#050505] border-r border-white/5 p-3 flex flex-col gap-1 max-md:hidden overflow-y-auto shrink-0">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all text-left w-full ${tab === t.id ? 'bg-[#ff2a5f]/12 text-[#ff2a5f]' : 'text-white/50 hover:bg-white/5 hover:text-white/70'}`}
            >
              <span className="material-icons text-[20px]">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>

        {/* Mobile tabs */}
        <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#050505] border-t border-white/5 flex justify-around p-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex flex-col items-center gap-0.5 px-2 py-2 rounded-xl text-[10px] min-w-[56px] transition-all ${tab === t.id ? 'text-[#ff2a5f]' : 'text-white/40'}`}
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
                    { label: 'Повідомлень', value: stats.totalMessages, icon: 'message', color: '#ff2a5f' },
                    { label: 'Міток на карті', value: stats.markersCount, icon: 'place', color: '#5ef5c4' },
                    { label: 'Приховано', value: stats.hiddenCount, icon: 'visibility_off', color: '#ffab40' },
                    { label: 'Заблоковано', value: stats.blockedCount, icon: 'block', color: '#ff5252' },
                    { label: 'Pending Geo', value: stats.pendingGeoCount, icon: 'pending', color: '#b388ff' },
                    { label: 'Монітор (хв)', value: stats.settings.monitorPeriod, icon: 'timer', color: '#ff2a5f' },
                    { label: 'TTL Система', value: stats.settings.ttlEnabled ? 'Увімк.' : 'Вимк.', icon: 'schedule', color: stats.settings.ttlEnabled ? '#5ef5c4' : '#ff5252' },
                  ].map((s, i) => (
                    <div key={i} className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5">
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
              <button onClick={loadStats} className="text-xs text-[#ff2a5f]/60 hover:text-[#ff2a5f] transition-colors">
                <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
              </button>
            </div>
          )}

          {/* ── CHAT REPORTS (MODERATION) ── */}
          {tab === 'reports' && (
            <div className="space-y-6 animate-[fadeIn_0.3s_ease]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <h2 className="text-xl font-semibold text-white/90">Скарги ({reports.filter(r => reportsFilter === 'ALL' || r.status === reportsFilter).length})</h2>
                  <select
                    value={reportsFilter}
                    onChange={e => setReportsFilter(e.target.value as any)}
                    className="bg-[#0a0a0b] backdrop-blur-3xl text-sm text-white/70 border border-white/10 rounded-xl px-3 py-1.5 focus:outline-none"
                  >
                    <option value="PENDING">Тільки нові</option>
                    <option value="ALL">Всі</option>
                  </select>
                </div>
                <button onClick={loadReports} className="text-xs text-[#ff2a5f]/60 hover:text-[#ff2a5f] transition-colors">
                  <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
                </button>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {reports
                  .filter(r => reportsFilter === 'ALL' || r.status === reportsFilter)
                  .map(report => (
                    <div key={report.id} className="bg-[#0a0a0b] backdrop-blur-3xl border border-white/5 rounded-2xl p-4 flex gap-4">
                      <div className="flex flex-col gap-2 flex-1">
                        <div className="flex items-center justify-between">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${report.status === 'PENDING' ? 'bg-orange-500/20 text-orange-400' :
                            report.status === 'RESOLVED' ? 'bg-green-500/20 text-green-400' :
                              'bg-zinc-500/20 text-zinc-400'
                            }`}>
                            {report.status}
                          </span>
                          <span className="text-xs text-white/30">{formatKyivTime(report.createdAt)}</span>
                        </div>

                        <div className="mt-2 text-sm text-white/50">
                          <span className="font-semibold text-white/70">Причина: </span> {report.reason}
                        </div>

                        <div className="bg-[#050505] border border-white/5 rounded-xl p-3 mt-1">
                          <span className="text-xs text-white/40 block mb-1">Оригінальне повідомлення (ID: <span className="font-mono">{report.messageId.split('-')[1] || report.messageId}</span>):</span>
                          <span className="text-sm text-white/80">{report.originalText || '<без тексту>'}</span>
                        </div>

                        <div className="text-xs text-white/40 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                          <span>Скаржник: <span className="text-[#ff2a5f]">{report.reporterNickname}</span></span>
                          {(report.reportedNickname || report.reportedDeviceId) && (
                            <span>Автор: <span className="text-red-400">{report.reportedNickname || 'ID ' + (report.reportedDeviceId || '').slice(0, 8)}</span></span>
                          )}
                        </div>
                      </div>

              {report.status === 'PENDING' && (
                <div className="flex flex-col gap-2 w-40 border-l border-white/5 pl-4 justify-center">
                  <button
                    onClick={async () => {
                      if (!confirm('Видалити повідомлення та закрити скаргу?')) return;
                      try {
                        await api(`/api/chat/message/${report.messageId}`, { method: 'DELETE' });
                        await api('/api/admin/chat/reports/resolve', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ reportId: report.id, action: 'RESOLVED' })
                        });
                        notify('Повідомлення видалено, скарга закрита', 'success');
                        loadReports();
                      } catch (e) {
                        notify('Помилка', 'error');
                      }
                    }}
                    className="bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs px-3 py-2 rounded-xl transition-colors border border-red-500/20 flex items-center justify-center"
                  >
                    <span className="material-icons text-[14px] mr-1">delete_forever</span>Видалити
                  </button>

                  <button
                    onClick={async () => {
                      try {
                        await api('/api/admin/chat/reports/resolve', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ reportId: report.id, action: 'REJECTED' })
                        });
                        notify('Скаргу відхилено', 'success');
                        loadReports();
                      } catch { notify('Помилка', 'error'); }
                    }}
                    className="bg-zinc-500/10 hover:bg-zinc-500/20 text-zinc-400 text-xs px-3 py-2 rounded-xl transition-colors border border-zinc-500/20 flex items-center justify-center"
                  >
                    <span className="material-icons text-[14px] mr-1">close</span>Відхилити
                  </button>

                  {(report.reportedNickname || report.reportedDeviceId) && (
                    <>
                      <button
                        onClick={async () => {
                          if (!confirm(`Заблокувати ${report.reportedNickname || 'користувача'}?`)) return;
                          try {
                            await api('/api/admin/chat/ban-user', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                nickname: report.reportedNickname || undefined,
                                deviceId: report.reportedDeviceId || undefined,
                                reason: `Скарга: ${report.reason}`,
                              })
                            });
                            notify('Користувача заблоковано', 'success');
                            loadReports();
                          } catch { notify('Помилка', 'error'); }
                        }}
                        className="bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 text-xs px-3 py-2 rounded-xl transition-colors border border-orange-500/20 flex items-center justify-center"
                      >
                        <span className="material-icons text-[14px] mr-1">block</span>Заблокувати
                      </button>

                      <button
                        onClick={async () => {
                          if (!confirm(`Видалити всі повідомлення від ${report.reportedNickname || 'цього користувача'}?`)) return;
                          try {
                            const res = await api<{ deleted: number }>('/api/admin/chat/delete-user-messages', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                nickname: report.reportedNickname || undefined,
                                deviceId: report.reportedDeviceId || undefined,
                              })
                            });
                            notify(`Видалено повідомлень: ${res?.deleted ?? 0}`, 'success');
                            loadReports();
                          } catch { notify('Помилка', 'error'); }
                        }}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs px-3 py-2 rounded-xl transition-colors border border-red-500/20 flex items-center justify-center"
                      >
                        <span className="material-icons text-[14px] mr-1">delete_sweep</span>Видалити всі
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  )
}

{/* ── MARKERS ── */ }
{
  tab === 'markers' && (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white/90">Мітки ({markers.length})</h2>
        <button onClick={() => { loadMarkers(); loadHidden(); }} className="text-xs text-[#ff2a5f]/60 hover:text-[#ff2a5f] transition-colors">
          <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
        </button>
      </div>

      {/* Add marker form */}
      <form onSubmit={addMarker} className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5 space-y-3">
        <h3 className="text-sm font-medium text-white/70 mb-2">Додати мітку</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <input placeholder="Lat" value={addForm.lat} onChange={e => setAddForm(f => ({ ...f, lat: e.target.value }))} className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/30" required />
          <input placeholder="Lng" value={addForm.lng} onChange={e => setAddForm(f => ({ ...f, lng: e.target.value }))} className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/30" required />
          <input placeholder="Місце" value={addForm.place} onChange={e => setAddForm(f => ({ ...f, place: e.target.value }))} className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/30" />
          <select value={addForm.threat_type} onChange={e => setAddForm(f => ({ ...f, threat_type: e.target.value }))} className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30">
            {threatTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <input placeholder="Текст повідомлення" value={addForm.text} onChange={e => setAddForm(f => ({ ...f, text: e.target.value }))} className="w-full bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/30" required />
        <button type="submit" className="bg-[#ff2a5f]/15 hover:bg-[#ff2a5f]/25 text-[#ff2a5f] text-sm px-4 py-2 rounded-xl transition-all border border-[#ff2a5f]/10">
          <span className="material-icons text-[14px] mr-1 align-middle">add</span>Додати
        </button>
      </form>

      {/* Markers table */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl border border-white/5 overflow-hidden">
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
                    <span className={`text-xs px-2 py-0.5 rounded-lg ${m.threat_type === 'shahed' ? 'bg-[#ff2a5f]/10 text-[#ff2a5f]' : m.threat_type === 'raketa' ? 'bg-red-400/10 text-red-400' : 'bg-[#ffab40]/10 text-[#ffab40]'}`}>
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
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5">
        <h3 className="text-sm font-medium text-white/70 mb-3">Приховані мітки ({hidden.length})</h3>
        {hidden.length === 0 ? (
          <div className="text-white/30 text-sm">Немає прихованих міток</div>
        ) : (
          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {hidden.map((h, i) => (
              <div key={i} className="flex items-center justify-between bg-[#050505] rounded-xl px-3 py-2 text-xs">
                <span className="text-white/40 truncate flex-1 mr-2">{h.text || `${h.lat}, ${h.lng}`}</span>
                <button onClick={() => unhideMarker(h.key)} className="text-[#5ef5c4]/60 hover:text-[#5ef5c4] text-xs px-2 py-1 rounded-lg hover:bg-[#5ef5c4]/10 transition-all whitespace-nowrap">
                  <span className="material-icons text-[14px] mr-0.5 align-middle">visibility</span>Показати
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

{/* ── MESSAGES ── */ }
{
  tab === 'messages' && (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white/90">Повідомлення (pending geo: {rawMsgs.length})</h2>
        <button onClick={loadRawMsgs} className="text-xs text-[#ff2a5f]/60 hover:text-[#ff2a5f] transition-colors">
          <span className="material-icons text-[14px] mr-1 align-middle">refresh</span>Оновити
        </button>
      </div>
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl border border-white/5 overflow-hidden">
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
                  <td className="px-4 py-2.5 text-xs text-[#ff2a5f]/60">{m.channel || m.source}</td>
                  <td className="px-4 py-2.5 text-white/60 text-xs">{(m.text || '').slice(0, 120)}{(m.text || '').length > 120 ? '...' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

{/* ── USERS ── */ }
{
  tab === 'users' && (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white/90">Заблоковані користувачі ({blocked.length})</h2>

      {/* Block form */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5">
        <h3 className="text-sm font-medium text-white/70 mb-2">Заблокувати користувача</h3>
        <form onSubmit={async (e) => {
          e.preventDefault();
          const input = (e.target as HTMLFormElement).elements.namedItem('blockId') as HTMLInputElement;
          if (input.value.trim()) {
            await blockUser(input.value.trim());
            input.value = '';
          }
        }} className="flex gap-2">
          <input name="blockId" placeholder="User ID" className="flex-1 bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/30" />
          <button type="submit" className="bg-red-400/15 hover:bg-red-400/25 text-red-400 text-sm px-4 py-2 rounded-xl transition-all border border-red-400/10">
            <span className="material-icons text-[14px] mr-1 align-middle">block</span>Блокувати
          </button>
        </form>
      </div>

      {/* Blocked list */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5">
        {blocked.length === 0 ? (
          <div className="text-white/30 text-sm">Немає заблокованих</div>
        ) : (
          <div className="space-y-2">
            {blocked.map((id, i) => (
              <div key={i} className="flex items-center justify-between bg-[#050505] rounded-xl px-3 py-2 text-xs">
                <span className="text-white/50 font-mono">{id}</span>
                <button onClick={() => unblockUser(id)} className="text-[#5ef5c4]/60 hover:text-[#5ef5c4] text-xs px-2 py-1 rounded-lg hover:bg-[#5ef5c4]/10 transition-all">
                  <span className="material-icons text-[14px] mr-0.5 align-middle">lock_open</span>Розблокувати
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

{/* ── SETTINGS ── */ }
{
  tab === 'settings' && (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white/90">Налаштування</h2>

      {/* Monitor period */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5 space-y-3">
        <h3 className="text-sm font-medium text-white/70">Період моніторингу (хвилини)</h3>
        <div className="flex items-center gap-3">
          <input
            type="number"
            min={1}
            max={360}
            value={settings.monitorPeriod}
            onChange={e => setSettings(s => ({ ...s, monitorPeriod: parseInt(e.target.value) || 30 }))}
            className="w-24 bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
          />
          <button onClick={() => saveMonitorPeriod(settings.monitorPeriod)} className="bg-[#ff2a5f]/15 hover:bg-[#ff2a5f]/25 text-[#ff2a5f] text-sm px-4 py-2 rounded-xl transition-all border border-[#ff2a5f]/10">
            Зберегти
          </button>
        </div>
      </div>

      {/* Confidence Threshold */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-5 border border-white/5 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-sm font-medium text-white/90">Поріг впевненості (Confidence Threshold)</h3>
            <p className="text-[11px] text-white/40 mt-1">Мінімальний % впевненості AI для відображення мітки на карті.</p>
          </div>
          <div className="text-2xl font-semibold" style={{ color: `hsl(${settings.minConfidence * 120}, 100%, 70%)` }}>
            {Math.round(settings.minConfidence * 100)}%
          </div>
        </div>

        <input
          type="range"
          min="0.1"
          max="1.0"
          step="0.05"
          value={settings.minConfidence}
          onChange={e => setSettings(s => ({ ...s, minConfidence: parseFloat(e.target.value) }))}
          onMouseUp={() => saveMinConfidence(settings.minConfidence)}
          onTouchEnd={() => saveMinConfidence(settings.minConfidence)}
          className="w-full h-2 bg-[#050505] rounded-lg appearance-none cursor-pointer accent-[#ff2a5f] outline-none border border-white/5"
        />
        <div className="flex justify-between text-[10px] text-white/30 px-1 font-mono">
          <span>10% (Все підряд)</span>
          <span>50% (Баланс)</span>
          <span>100% (Тільки точні)</span>
        </div>
      </div>

      {/* TTL toggle */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5 space-y-3">
        <h3 className="text-sm font-medium text-white/70">TTL Система (автоматичне видалення старих міток)</h3>
        <button onClick={toggleTTL} className={`px-4 py-2 rounded-xl text-sm transition-all border ${settings.ttlEnabled ? 'bg-[#5ef5c4]/15 text-[#5ef5c4] border-[#5ef5c4]/20' : 'bg-red-400/15 text-red-400 border-red-400/20'}`}>
          {settings.ttlEnabled ? 'Увімкнено' : 'Вимкнено'} — натисніть щоб змінити
        </button>
      </div>

      {/* Cache clear */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-4 border border-white/5 space-y-3">
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
  )
}

{
  tab === 'corrections' && (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white/90">Корекції гео-резолюції</h2>
      <p className="text-sm text-white/50">Виправляйте помилкові координати — система навчиться автоматично.</p>

      {/* Add correction form */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-5 border border-white/5 space-y-4">
        <h3 className="text-sm font-medium text-white/70 flex items-center gap-2">
          <span className="material-icons text-[18px] text-[#ff2a5f]">add_location</span>
          Нова корекція
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <input
            placeholder="Назва місця"
            value={corrForm.place_name}
            onChange={e => setCorrForm(f => ({ ...f, place_name: e.target.value }))}
            className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
          />
          <input
            placeholder="Правильна широта"
            type="number"
            step="0.0001"
            value={corrForm.correct_lat}
            onChange={e => setCorrForm(f => ({ ...f, correct_lat: e.target.value }))}
            className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
          />
          <input
            placeholder="Правильна довгота"
            type="number"
            step="0.0001"
            value={corrForm.correct_lng}
            onChange={e => setCorrForm(f => ({ ...f, correct_lng: e.target.value }))}
            className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
          />
          <input
            placeholder="Правильна область"
            value={corrForm.correct_oblast}
            onChange={e => setCorrForm(f => ({ ...f, correct_oblast: e.target.value }))}
            className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
          />
          <select
            value={corrForm.reason}
            onChange={e => setCorrForm(f => ({ ...f, reason: e.target.value }))}
            className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
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
            className="bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[#ff2a5f]/30"
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
          className="bg-[#ff2a5f]/15 hover:bg-[#ff2a5f]/25 text-[#ff2a5f] text-sm px-5 py-2.5 rounded-xl transition-all border border-[#ff2a5f]/10"
        >
          <span className="material-icons text-[14px] mr-1 align-middle">save</span>
          Зберегти корекцію
        </button>
      </div>

      {/* Corrections list */}
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl border border-white/5 overflow-hidden">
        <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
          <h3 className="text-sm font-medium text-white/70">Останні корекції ({corrections.length})</h3>
        </div>
        {corrections.length === 0 ? (
          <div className="p-8 text-center text-white/30 text-sm">Корекцій ще немає</div>
        ) : (
          <div className="max-h-[400px] overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-[#050505] sticky top-0">
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
                      <span className="inline-block bg-[#ff2a5f]/10 text-[#ff2a5f] text-[10px] px-2 py-0.5 rounded-full">
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
      <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-5 border border-white/5 space-y-3">
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
  )
}

{/* ── FEEDBACK ── */ }
{
  tab === 'feed' && (() => {
    const statusColors: Record<string, string> = {
      processed: '#5ef5c4', skipped: '#ffab40', dropped: '#ff5252',
      deduped: '#b388ff', chain_update: '#ff2a5f', error: '#ff1744',
      retargeted: '#40c4ff',
    };
    const statusLabels: Record<string, string> = {
      processed: 'Оброблено', skipped: 'Пропущено', dropped: 'Відхилено',
      deduped: 'Дедупліковано', chain_update: 'Ланцюг', error: 'Помилка',
      retargeted: 'Ретаргет',
    };
    const statuses = ['all', 'processed', 'skipped', 'dropped', 'deduped', 'chain_update', 'retargeted', 'error'];
    const filtered = feedFilter === 'all' ? feedEntries : feedEntries.filter(e => e.status === feedFilter);
    const counts: Record<string, number> = {};
    for (const e of feedEntries) counts[e.status] = (counts[e.status] || 0) + 1;

    return (
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-xl font-semibold text-white/90">
            Лента обробки
            <span className="text-sm font-normal text-white/30 ml-2">({filtered.length})</span>
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFeedPaused(p => !p)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-all border ${feedPaused ? 'bg-[#ff5252]/15 text-[#ff5252] border-[#ff5252]/20' : 'bg-[#5ef5c4]/10 text-[#5ef5c4] border-[#5ef5c4]/20'}`}
            >
              <span className="material-icons text-[14px] align-middle mr-1">{feedPaused ? 'pause' : 'play_arrow'}</span>
              {feedPaused ? 'Пауза' : 'Live'}
            </button>
            <button onClick={loadFeed} className="text-xs text-[#ff2a5f]/60 hover:text-[#ff2a5f] transition-colors">
              <span className="material-icons text-[14px] align-middle">refresh</span>
            </button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-2 flex-wrap">
          {statuses.map(s => (
            <button
              key={s}
              onClick={() => setFeedFilter(s)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-all border ${feedFilter === s
                ? 'bg-[#ff2a5f]/15 text-[#ff2a5f] border-[#ff2a5f]/20'
                : 'text-white/40 border-white/5 hover:bg-white/5 hover:text-white/60'
                }`}
            >
              {s === 'all' ? `Усі (${feedEntries.length})` : `${statusLabels[s] || s} (${counts[s] || 0})`}
            </button>
          ))}
        </div>

        {/* Feed list */}
        <div ref={feedRef} className="space-y-2 max-h-[calc(100vh-220px)] overflow-y-auto pr-1">
          {filtered.length === 0 ? (
            <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-8 border border-white/5 text-center text-white/30 text-sm">
              {feedEntries.length === 0 ? 'Очікування повідомлень...' : 'Немає повідомлень з цим фільтром'}
            </div>
          ) : filtered.map(entry => {
            const borderColor = statusColors[entry.status] || '#555';
            const isOpen = feedExpanded === entry._id;
            return (
              <div
                key={entry._id}
                className="bg-[#0a0a0b] backdrop-blur-3xl rounded-xl border border-white/5 overflow-hidden"
                style={{ borderLeftWidth: 3, borderLeftColor: borderColor }}
              >
                {/* Compact row */}
                <button
                  onClick={() => setFeedExpanded(isOpen ? null : entry._id)}
                  className="w-full px-3 py-2.5 flex items-center gap-2 hover:bg-white/[0.02] transition-colors text-left"
                >
                  <span className="material-icons text-[12px] text-white/20 transition-transform" style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>chevron_right</span>
                  {/* Status badge */}
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-md font-medium shrink-0"
                    style={{ backgroundColor: borderColor + '18', color: borderColor }}
                  >
                    {statusLabels[entry.status] || entry.status}
                  </span>
                  {/* Threat type */}
                  {entry.threat_type && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/50 font-mono shrink-0">{entry.threat_type}</span>
                  )}
                  {/* Channel */}
                  {entry.channel_name && (
                    <span className="text-[10px] text-[#ff2a5f]/70 shrink-0 max-w-[120px] truncate">{entry.channel_name}</span>
                  )}
                  {/* Place / reason */}
                  <span className="text-xs text-white/60 flex-1 truncate">
                    {entry.place || entry.reason || entry.msg_text?.slice(0, 60) || '—'}
                  </span>
                  {/* Region pill */}
                  {entry.region && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/40 shrink-0 hidden sm:inline">{entry.region}</span>
                  )}
                  {/* Confidence */}
                  {entry.confidence != null && entry.confidence > 0 && (
                    <span className={`text-[10px] font-mono shrink-0 ${entry.confidence >= 0.7 ? 'text-[#5ef5c4]' : entry.confidence >= 0.3 ? 'text-[#ffab40]' : 'text-[#ff5252]'}`}>
                      {(entry.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {/* Time */}
                  <span className="text-[10px] text-white/20 shrink-0 font-mono">
                    {(() => { try { const d = new Date(entry.ts); return d.toLocaleTimeString('uk-UA', { timeZone: 'Europe/Kyiv', hour: '2-digit', minute: '2-digit', second: '2-digit' }); } catch { return ''; } })()}
                  </span>
                </button>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="border-t border-white/5 px-3 py-3 space-y-3">
                    {/* Message text */}
                    {entry.msg_text && (
                      <div className="bg-[#050505] rounded-lg p-2.5 text-xs text-white/60 whitespace-pre-wrap max-h-24 overflow-y-auto">{entry.msg_text}</div>
                    )}
                    {/* Meta grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1.5 text-[11px]">
                      {entry.channel_name && <div><span className="text-white/30">Канал:</span> <span className="text-white/60">{entry.channel_name}</span></div>}
                      {entry.threat_type && <div><span className="text-white/30">Тип:</span> <span className="text-white/60">{entry.threat_type}</span></div>}
                      {entry.parser && <div><span className="text-white/30">Парсер:</span> <span className="text-white/60">{entry.parser}</span></div>}
                      {entry.entities_count != null && <div><span className="text-white/30">Сутностей:</span> <span className="text-white/60">{entry.entities_count}</span></div>}
                      {entry.place && <div><span className="text-white/30">Місце:</span> <span className="text-white/60">{entry.place}</span></div>}
                      {entry.region && <div><span className="text-white/30">Область:</span> <span className="text-white/60">{entry.region}</span></div>}
                      {entry.lat != null && <div><span className="text-white/30">Coords:</span> <span className="text-white/60 font-mono">{entry.lat.toFixed(3)}, {entry.lng?.toFixed(3)}</span></div>}
                      {entry.speed_kmh != null && <div><span className="text-white/30">Швидкість:</span> <span className="text-white/60">{entry.speed_kmh} км/г</span></div>}
                      {entry.course_bearing != null && <div><span className="text-white/30">Курс:</span> <span className="text-white/60">{entry.course_bearing}°</span></div>}
                      {entry.track_id && <div><span className="text-white/30">Track:</span> <span className="text-white/60 font-mono">{entry.track_id}</span></div>}
                      {entry.marker_id && <div><span className="text-white/30">Marker:</span> <span className="text-white/60 font-mono">{entry.marker_id}</span></div>}
                      {entry.resolve_status && <div><span className="text-white/30">Resolve:</span> <span className="text-white/60">{entry.resolve_status}</span></div>}
                      {entry.confidence != null && <div><span className="text-white/30">Confidence:</span> <span className="text-white/60">{(entry.confidence * 100).toFixed(1)}%</span></div>}
                      {entry.origin && <div><span className="text-white/30">Origin:</span> <span className="text-white/60">{entry.origin}</span></div>}
                      {entry.reason && <div className="col-span-2"><span className="text-white/30">Причина:</span> <span className="text-[#ffab40]/80">{entry.reason}</span></div>}
                      {entry.msg_id != null && <div><span className="text-white/30">msg_id:</span> <span className="text-white/50 font-mono">{entry.msg_id}</span></div>}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  })()
}

{
  tab === 'feedback' && (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-xl font-semibold text-white/90">Зворотній зв&apos;язок ({feedbackTotal})</h2>
        <div className="flex items-center gap-2">
          {['all', 'open', 'in_progress', 'resolved', 'closed'].map(s => (
            <button
              key={s}
              onClick={() => setFeedbackFilter(s)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-all border ${feedbackFilter === s
                ? 'bg-[#ff2a5f]/15 text-[#ff2a5f] border-[#ff2a5f]/20'
                : 'text-white/40 border-white/5 hover:bg-white/5 hover:text-white/60'
                }`}
            >
              {s === 'all' ? 'Усі' : s === 'open' ? 'Відкриті' : s === 'in_progress' ? 'В роботі' : s === 'resolved' ? 'Вирішено' : 'Закрито'}
            </button>
          ))}
          <button onClick={loadFeedback} className="text-xs text-[#ff2a5f]/60 hover:text-[#ff2a5f] transition-colors ml-2">
            <span className="material-icons text-[14px] align-middle">refresh</span>
          </button>
        </div>
      </div>

      {feedbackTickets.length === 0 ? (
        <div className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl p-8 border border-white/5 text-center text-white/30 text-sm">Немає звернень</div>
      ) : (
        <div className="space-y-3">
          {feedbackTickets.map(ticket => {
            const isExpanded = expandedTicket === ticket.id;
            const statusColor = ticket.status === 'open' ? '#ff2a5f' : ticket.status === 'in_progress' ? '#ffab40' : ticket.status === 'resolved' ? '#5ef5c4' : '#ff5252';
            return (
              <div key={ticket.id} className="bg-[#0a0a0b] backdrop-blur-3xl rounded-2xl border border-white/5 overflow-hidden">
                {/* Ticket header */}
                <button
                  onClick={() => setExpandedTicket(isExpanded ? null : ticket.id)}
                  className="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/[0.02] transition-colors text-left"
                >
                  <span className="material-icons text-[14px] text-white/30 transition-transform" style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>chevron_right</span>
                  <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: statusColor }} />
                  <span className={`text-[10px] px-2 py-0.5 rounded-lg shrink-0 ${ticket.type === 'bug' ? 'bg-red-400/10 text-red-400' : ticket.type === 'suggestion' ? 'bg-[#b388ff]/10 text-[#b388ff]' : 'bg-[#ff2a5f]/10 text-[#ff2a5f]'}`}>
                    {ticket.type === 'bug' ? 'Баг' : ticket.type === 'suggestion' ? 'Пропозиція' : 'Загальне'}
                  </span>
                  <span className="text-sm text-white/80 flex-1 truncate">{ticket.message}</span>
                  <span className="text-[10px] text-white/30 shrink-0">{ticket.device} {ticket.app_version}</span>
                  {ticket.responses.length > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#ff2a5f]/10 text-[#ff2a5f] shrink-0">{ticket.responses.length}</span>
                  )}
                  <span className="text-[10px] text-white/20 shrink-0">{formatKyivTime(ticket.created_at)}</span>
                </button>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="border-t border-white/5 px-4 py-4 space-y-4">
                    {/* Full message */}
                    <div className="bg-[#050505] rounded-xl p-3 text-sm text-white/70 whitespace-pre-wrap">{ticket.message}</div>

                    {/* Meta */}
                    <div className="flex items-center gap-4 text-[11px] text-white/30 flex-wrap">
                      <span>ID: <span className="font-mono text-white/50">{ticket.id}</span></span>
                      <span>Device: <span className="text-white/50">{ticket.device_id?.slice(0, 12)}...</span></span>
                      <span>Оновлено: {formatKyivTime(ticket.updated_at)}</span>
                    </div>

                    {/* Status control */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white/40">Статус:</span>
                      {['open', 'in_progress', 'resolved', 'closed'].map(s => (
                        <button
                          key={s}
                          onClick={() => changeFeedbackStatus(ticket.id, s)}
                          className={`text-[11px] px-2.5 py-1 rounded-lg transition-all border ${ticket.status === s
                            ? 'border-white/20 text-white/80 bg-white/10'
                            : 'border-white/5 text-white/30 hover:bg-white/5 hover:text-white/50'
                            }`}
                        >
                          {s === 'open' ? 'Відкрито' : s === 'in_progress' ? 'В роботі' : s === 'resolved' ? 'Вирішено' : 'Закрито'}
                        </button>
                      ))}
                    </div>

                    {/* Responses timeline */}
                    {ticket.responses.length > 0 && (
                      <div className="space-y-2 mt-2">
                        <h4 className="text-xs text-white/40 font-medium">Відповіді</h4>
                        {ticket.responses.map(resp => (
                          <div key={resp.id} className={`rounded-xl p-3 text-sm ${resp.author === 'admin' ? 'bg-[#ff2a5f]/5 border border-[#ff2a5f]/10 ml-4' : 'bg-[#050505] mr-4'}`}>
                            <div className="flex items-center justify-between mb-1">
                              <span className={`text-[10px] font-medium ${resp.author === 'admin' ? 'text-[#ff2a5f]' : 'text-[#ffab40]'}`}>
                                {resp.author === 'admin' ? '👤 Адмін' : '📱 Користувач'}
                              </span>
                              <span className="text-[10px] text-white/20">{formatKyivTime(resp.created_at)}</span>
                            </div>
                            <p className="text-white/70 whitespace-pre-wrap">{resp.message}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Reply form */}
                    <div className="flex gap-2 mt-2">
                      <input
                        value={replyText[ticket.id] || ''}
                        onChange={e => setReplyText(prev => ({ ...prev, [ticket.id]: e.target.value }))}
                        placeholder="Написати відповідь..."
                        className="flex-1 bg-[#050505] border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#ff2a5f]/30"
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); respondToFeedback(ticket.id); } }}
                      />
                      <button
                        onClick={() => respondToFeedback(ticket.id)}
                        disabled={replyingSending === ticket.id || !replyText[ticket.id]?.trim()}
                        className="bg-[#ff2a5f]/15 hover:bg-[#ff2a5f]/25 text-[#ff2a5f] text-sm px-4 py-2 rounded-xl transition-all border border-[#ff2a5f]/10 disabled:opacity-30"
                      >
                        {replyingSending === ticket.id ? '...' : 'Відповісти'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
      );
          })}
    </div>
  )
}
    </div>
  )
}
        </main >
      </div >
    </div >
  );
}
