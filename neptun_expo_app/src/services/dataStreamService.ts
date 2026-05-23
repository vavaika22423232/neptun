import { endpoints } from '../config/api';
import { absoluteUrl } from '../config/api';

type Listener<T> = (payload: T) => void;
type EventMap = {
  alarm_update: unknown[];
  marker_new: Record<string, unknown>;
  markers_refresh: Record<string, unknown>;
  marker_update: Record<string, unknown>;
  marker_delete: Record<string, unknown>;
  track_update: Record<string, unknown>;
  connected: Record<string, unknown>;
  online: Record<string, unknown>;
  new_message: Record<string, unknown>;
  delete_message: Record<string, unknown>;
  reaction: Record<string, unknown>;
  edit_message: Record<string, unknown>;
  typing: Record<string, unknown>;
};

class DataStreamService {
  private source: EventSource | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private listeners = new Map<keyof EventMap, Set<Listener<never>>>();
  private errorListeners = new Set<() => void>();
  private wanted = false;

  onError(listener: () => void): () => void {
    this.errorListeners.add(listener);
    return () => this.errorListeners.delete(listener);
  }

  on<K extends keyof EventMap>(type: K, listener: Listener<EventMap[K]>): () => void {
    const set = this.listeners.get(type) ?? new Set();
    set.add(listener as Listener<never>);
    this.listeners.set(type, set);
    return () => set.delete(listener as Listener<never>);
  }

  connect(): void {
    if (this.source || this.wanted) return;
    this.wanted = true;
    this.open();
  }

  forceReconnect(): void {
    this.closeSource();
    if (this.wanted) this.open();
  }

  disconnect(): void {
    this.wanted = false;
    this.closeSource();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
  }

  private open(): void {
    this.closeSource();
    try {
      this.source = new EventSource(absoluteUrl(endpoints.chatStream));
      this.source.onopen = () => {
        this.reconnectDelay = 1000;
      };
      this.source.onmessage = (event) => this.processFrame(undefined, event.data);
      for (const type of this.listeners.keys()) {
        this.source.addEventListener(type, (event) => this.processFrame(type, (event as MessageEvent).data));
      }
      this.source.onerror = () => this.scheduleReconnect();
    } catch {
      this.scheduleReconnect();
    }
  }

  private processFrame(eventType: string | undefined, raw: string): void {
    const text = raw.trim();
    if (!text || text.startsWith('<')) return;
    try {
      const decoded = JSON.parse(text) as unknown;
      let type = eventType as keyof EventMap | undefined;
      let payload: unknown = decoded;
      if (decoded && typeof decoded === 'object' && 'type' in decoded) {
        const obj = decoded as { type?: string; data?: unknown };
        type = (obj.type ?? type) as keyof EventMap;
        payload = obj.data;
      }
      if (!type) return;
      this.listeners.get(type)?.forEach((listener) => listener(payload as never));
    } catch {
      /* ignore malformed keepalive frames */
    }
  }

  private scheduleReconnect(): void {
    if (!this.wanted) return;
    this.errorListeners.forEach((fn) => fn());
    this.closeSource();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const delay = this.reconnectDelay;
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    this.reconnectTimer = setTimeout(() => this.open(), delay);
  }

  private closeSource(): void {
    this.source?.close();
    this.source = null;
  }
}

export const dataStreamService = new DataStreamService();
