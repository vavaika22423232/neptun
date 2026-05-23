import { NextResponse } from 'next/server';
import { requireChatAuth, type ChatIdentity } from './chat-auth';
import { sanitizeDeviceId } from './monetization/entitlement-store';
import { logSecurityEvent } from './security-log';

/** When true, sensitive device-scoped routes require a JWT whose deviceId matches the caller. */
export function isDeviceJwtRequired(): boolean {
  const flag = process.env.REQUIRE_DEVICE_JWT;
  if (flag === '0' || flag === 'false') return false;
  if (flag === '1' || flag === 'true') return true;
  return process.env.NODE_ENV === 'production';
}

export type DeviceAuthResult =
  | { ok: true; deviceId: string; identity?: ChatIdentity }
  | { ok: false; response: NextResponse };

/**
 * Validates that the caller owns `claimedDeviceId`.
 * - JWT required in production (configurable via REQUIRE_DEVICE_JWT).
 * - Token deviceId must match sanitized claimed id.
 */
export function requireDeviceAuth(
  request: Request,
  claimedDeviceId: string | null | undefined,
): DeviceAuthResult {
  const deviceId = sanitizeDeviceId(claimedDeviceId ?? null);
  if (!deviceId) {
    return {
      ok: false,
      response: NextResponse.json({ error: 'bad_device_id' }, { status: 400 }),
    };
  }

  if (!isDeviceJwtRequired()) {
    return { ok: true, deviceId };
  }

  const auth = requireChatAuth(request);
  if (auth instanceof Response) {
    logSecurityEvent('device_auth_failed', { reason: 'missing_or_invalid_jwt' });
    return { ok: false, response: auth };
  }

  if (auth.deviceId !== deviceId) {
    logSecurityEvent('device_auth_failed', {
      reason: 'device_mismatch',
      claimed: deviceId.slice(0, 8),
    });
    return {
      ok: false,
      response: NextResponse.json({ error: 'device_mismatch' }, { status: 403 }),
    };
  }

  return { ok: true, deviceId, identity: auth };
}

export async function requireDeviceAuthFromJson(
  request: Request,
  body: Record<string, unknown>,
  field = 'deviceId',
): Promise<DeviceAuthResult> {
  const alt = field === 'deviceId' ? body.device_id : undefined;
  const raw = body[field] ?? alt;
  return requireDeviceAuth(request, typeof raw === 'string' ? raw : null);
}
