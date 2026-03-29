import crypto from 'crypto';

/**
 * Best-effort client IP for rate limits / abuse guards (trust proxy headers from nginx).
 */
export function getClientIp(request: Request): string {
  const xf = request.headers.get('x-forwarded-for');
  if (xf) {
    const first = xf.split(',')[0]?.trim();
    if (first) return first.slice(0, 64);
  }
  const real = request.headers.get('x-real-ip')?.trim();
  if (real) return real.slice(0, 64);
  return 'unknown';
}

export function ipRedisTag(ip: string): string {
  return crypto.createHash('sha256').update(ip).digest('hex').slice(0, 24);
}
