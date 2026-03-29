import { NextResponse } from 'next/server';

/** Upper bound for authenticated ingest JSON (single marker or batch). */
export const MAX_INGEST_BODY_BYTES = 768 * 1024;

/**
 * If Content-Length is present and exceeds the limit, return 413.
 * (Chunked requests without Content-Length are still bounded by the runtime;
 *  this stops typical large accidental/malicious posts early.)
 */
export function ingestBodyTooLargeResponse(request: Request): NextResponse | null {
  const raw = request.headers.get('content-length');
  if (raw == null) return null;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) return null;
  if (n > MAX_INGEST_BODY_BYTES) {
    return NextResponse.json(
      { error: 'Payload too large', max_bytes: MAX_INGEST_BODY_BYTES },
      { status: 413 },
    );
  }
  return null;
}
