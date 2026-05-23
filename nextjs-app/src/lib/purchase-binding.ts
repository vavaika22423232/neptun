import crypto from 'crypto';
import { getRedis } from './redis';
import { logSecurityEvent } from './security-log';

const TOKEN_BIND_PREFIX = 'purchase_bind:token:';
const ORIGINAL_BIND_PREFIX = 'purchase_bind:original:';

function hashKey(raw: string): string {
  return crypto.createHash('sha256').update(raw).digest('hex').slice(0, 40);
}

export type PurchaseBindResult =
  | { ok: true }
  | { ok: false; reason: 'bound_other_device' };

/** Prevent one store receipt from being bound to multiple devices. */
export async function assertPurchaseBindAllowed(
  deviceId: string,
  purchaseToken: string,
  originalTransactionId?: string | null,
): Promise<PurchaseBindResult> {
  const redis = getRedis();
  const tokenKey = `${TOKEN_BIND_PREFIX}${hashKey(purchaseToken.trim())}`;

  const existingToken = await redis.get(tokenKey);
  if (existingToken && existingToken !== deviceId) {
    logSecurityEvent('purchase_bind_conflict', { device: deviceId });
    return { ok: false, reason: 'bound_other_device' };
  }

  if (originalTransactionId?.trim()) {
    const origKey = `${ORIGINAL_BIND_PREFIX}${hashKey(originalTransactionId.trim())}`;
    const existingOrig = await redis.get(origKey);
    if (existingOrig && existingOrig !== deviceId) {
      logSecurityEvent('purchase_bind_conflict', { device: deviceId });
      return { ok: false, reason: 'bound_other_device' };
    }
  }

  return { ok: true };
}

export async function bindPurchaseToDevice(
  deviceId: string,
  purchaseToken: string,
  originalTransactionId?: string | null,
): Promise<void> {
  const redis = getRedis();
  const tokenKey = `${TOKEN_BIND_PREFIX}${hashKey(purchaseToken.trim())}`;
  await redis.set(tokenKey, deviceId);

  if (originalTransactionId?.trim()) {
    const origKey = `${ORIGINAL_BIND_PREFIX}${hashKey(originalTransactionId.trim())}`;
    await redis.set(origKey, deviceId);
  }
}
