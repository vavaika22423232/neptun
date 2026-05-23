type SecurityEvent =
  | 'device_auth_failed'
  | 'rate_limit_hit'
  | 'admin_auth_failed'
  | 'purchase_bind_conflict'
  | 'feedback_access_denied'
  | 'validation_failed';

function redact(value: unknown): string {
  if (value == null) return '';
  const s = String(value);
  if (s.length <= 8) return '***';
  return `${s.slice(0, 4)}…${s.slice(-2)}`;
}

/** Structured security logs — never log secrets, tokens, or full device ids. */
export function logSecurityEvent(event: SecurityEvent, meta?: Record<string, unknown>): void {
  const safe: Record<string, string> = { event };
  if (meta) {
    for (const [k, v] of Object.entries(meta)) {
      if (/token|secret|password|purchase/i.test(k)) continue;
      if (k.includes('device') && typeof v === 'string') {
        safe[k] = redact(v);
      } else if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
        safe[k] = String(v);
      }
    }
  }
  console.warn('[SECURITY]', JSON.stringify(safe));
}
