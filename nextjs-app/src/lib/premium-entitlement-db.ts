/**
 * Server-side Pro entitlement (Redis).
 * Binds deviceId → verified purchase token so the app can re-check and revoke faked local flags.
 */

import { getRedis } from '@/lib/redis';

const KEY_PREFIX = 'premium_entitlement:';

export interface PremiumEntitlementRecord {
  productId: string;
  purchaseToken: string;
  source: string;
  lastVerifiedAt: string; // ISO
  registeredAt: string;
}

function key(deviceId: string) {
  return `${KEY_PREFIX}${deviceId}`;
}

export async function getEntitlement(deviceId: string): Promise<PremiumEntitlementRecord | null> {
  const raw = await getRedis().hgetall(key(deviceId));
  if (!raw || !raw.purchaseToken || !raw.productId) return null;
  return {
    productId: raw.productId,
    purchaseToken: raw.purchaseToken,
    source: raw.source || 'google_play',
    lastVerifiedAt: raw.lastVerifiedAt || raw.registeredAt || '',
    registeredAt: raw.registeredAt || '',
  };
}

export async function saveEntitlement(
  deviceId: string,
  data: Omit<PremiumEntitlementRecord, 'lastVerifiedAt' | 'registeredAt'> & {
    lastVerifiedAt?: string;
    registeredAt?: string;
  }
): Promise<void> {
  const now = new Date().toISOString();
  const rec: Record<string, string> = {
    productId: data.productId,
    purchaseToken: data.purchaseToken,
    source: data.source,
    lastVerifiedAt: data.lastVerifiedAt ?? now,
    registeredAt: data.registeredAt ?? now,
  };
  await getRedis().hset(key(deviceId), rec);
}

export async function updateLastVerified(deviceId: string, iso: string): Promise<void> {
  await getRedis().hset(key(deviceId), 'lastVerifiedAt', iso);
}

export async function deleteEntitlement(deviceId: string): Promise<void> {
  await getRedis().del(key(deviceId));
}

/** Skip live Google call if last verify was within this window (ms). */
export const ENTITLEMENT_REVERIFY_MS = 6 * 60 * 60 * 1000; // 6h
