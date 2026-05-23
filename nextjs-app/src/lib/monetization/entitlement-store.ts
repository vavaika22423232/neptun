/**
 * Device entitlements — Redis primary (existing premium_entitlement keys), optional PG mirror.
 */

import { getRedis } from '@/lib/redis';
import type { PlanId, SubscriptionStatus } from './plans';
import { buildEntitlements, planFromProductId, type EntitlementsPayload } from './plans';

const KEY_PREFIX = 'premium_entitlement:';
const USER_PREFIX = 'monetization:user:';
const DEVICE_USER_PREFIX = 'monetization:device_user:';

export interface StoredEntitlement {
  userId: string;
  deviceId: string;
  productId: string;
  purchaseToken: string;
  source: 'google_play' | 'app_store' | 'lifetime' | 'admin_grant';
  plan: PlanId;
  status: SubscriptionStatus;
  expiresAt: string | null;
  originalTransactionId: string | null;
  registeredAt: string;
  lastVerifiedAt: string;
}

function entitlementKey(deviceId: string) {
  return `${KEY_PREFIX}${deviceId}`;
}

function userKey(userId: string) {
  return `${USER_PREFIX}${userId}`;
}

function deviceUserKey(deviceId: string) {
  return `${DEVICE_USER_PREFIX}${deviceId}`;
}

export function sanitizeDeviceId(raw: string | null): string | null {
  if (!raw || typeof raw !== 'string') return null;
  const s = raw.trim();
  if (s.length < 8 || s.length > 200) return null;
  if (!/^[\w.-]+$/.test(s)) return null;
  return s;
}

export function createUserId(deviceId: string): string {
  return `u_${deviceId.slice(0, 32)}`;
}

export async function ensureUserForDevice(
  deviceId: string,
  meta?: { platform?: string; appVersion?: string; locale?: string },
): Promise<{ userId: string; created: boolean }> {
  const redis = getRedis();
  const existing = await redis.get(deviceUserKey(deviceId));
  if (existing) {
    if (meta) {
      await redis.hset(userKey(existing), {
        ...(meta.platform ? { platform: meta.platform } : {}),
        ...(meta.appVersion ? { app_version: meta.appVersion } : {}),
        ...(meta.locale ? { locale: meta.locale } : {}),
        last_seen_at: new Date().toISOString(),
      });
    }
    return { userId: existing, created: false };
  }

  const userId = createUserId(deviceId);
  const now = new Date().toISOString();
  await redis.set(deviceUserKey(deviceId), userId);
  await redis.hset(userKey(userId), {
    id: userId,
    created_at: now,
    updated_at: now,
    last_seen_at: now,
    platform: meta?.platform ?? 'unknown',
    app_version: meta?.appVersion ?? '',
    locale: meta?.locale ?? 'uk',
  });
  return { userId, created: true };
}

export async function getStoredEntitlement(deviceId: string): Promise<StoredEntitlement | null> {
  const raw = await getRedis().hgetall(entitlementKey(deviceId));
  if (!raw?.purchaseToken || !raw?.productId) return null;

  const plan = (raw.plan as PlanId) || planFromProductId(raw.productId);
  const userId = raw.userId || (await getRedis().get(deviceUserKey(deviceId))) || createUserId(deviceId);

  return {
    userId,
    deviceId,
    productId: raw.productId,
    purchaseToken: raw.purchaseToken,
    source: (raw.source as StoredEntitlement['source']) || 'google_play',
    plan,
    status: (raw.status as SubscriptionStatus) || 'active',
    expiresAt: raw.expiresAt || null,
    originalTransactionId: raw.originalTransactionId || null,
    registeredAt: raw.registeredAt || '',
    lastVerifiedAt: raw.lastVerifiedAt || raw.registeredAt || '',
  };
}

export async function saveStoredEntitlement(rec: Omit<StoredEntitlement, 'registeredAt' | 'lastVerifiedAt'> & {
  registeredAt?: string;
  lastVerifiedAt?: string;
}): Promise<void> {
  const now = new Date().toISOString();
  await getRedis().hset(entitlementKey(rec.deviceId), {
    userId: rec.userId,
    productId: rec.productId,
    purchaseToken: rec.purchaseToken,
    source: rec.source,
    plan: rec.plan,
    status: rec.status,
    expiresAt: rec.expiresAt ?? '',
    originalTransactionId: rec.originalTransactionId ?? '',
    registeredAt: rec.registeredAt ?? now,
    lastVerifiedAt: rec.lastVerifiedAt ?? now,
  });
  await getRedis().set(deviceUserKey(rec.deviceId), rec.userId);
}

export async function deleteStoredEntitlement(deviceId: string): Promise<void> {
  await getRedis().del(entitlementKey(deviceId));
}

export async function updateLastVerified(deviceId: string, iso: string): Promise<void> {
  await getRedis().hset(entitlementKey(deviceId), 'lastVerifiedAt', iso);
}

export async function resolveEntitlementsForDevice(deviceId: string): Promise<EntitlementsPayload> {
  const stored = await getStoredEntitlement(deviceId);
  if (!stored) {
    return buildEntitlements('free');
  }

  if (stored.expiresAt) {
    const exp = Date.parse(stored.expiresAt);
    if (Number.isFinite(exp) && exp < Date.now()) {
      return buildEntitlements('free', { status: 'expired', productId: stored.productId });
    }
  }

  return buildEntitlements(stored.plan, {
    expiresAt: stored.expiresAt,
    status: stored.status,
    productId: stored.productId,
  });
}

export const ENTITLEMENT_REVERIFY_MS = 6 * 60 * 60 * 1000;
