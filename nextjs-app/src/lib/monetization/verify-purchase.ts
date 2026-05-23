/**
 * Unified purchase verification → plan + stored entitlement.
 */

import {
  assertPremiumPurchase,
  type PremiumAssertResult,
} from '@/lib/iap-assert-premium';
import {
  assertPurchaseBindAllowed,
  bindPurchaseToDevice,
} from '@/lib/purchase-binding';
import {
  planFromProductId,
  type PlanId,
  ALL_KNOWN_PRODUCT_IDS,
} from './plans';
import {
  ensureUserForDevice,
  saveStoredEntitlement,
  sanitizeDeviceId,
  type StoredEntitlement,
} from './entitlement-store';

export { ALL_KNOWN_PRODUCT_IDS };

export type VerifyPurchaseInput = {
  deviceId: string;
  productId: string;
  purchaseToken: string;
  source?: 'google_play' | 'app_store';
  platform?: string;
  appVersion?: string;
  expiresAt?: string | null;
  originalTransactionId?: string | null;
};

export type VerifyPurchaseResult =
  | { ok: true; plan: PlanId; entitled: true }
  | { ok: false; reason: 'invalid' | 'pending' | 'transient' | 'misconfigured' | 'bad_input' };

function mapAssert(r: PremiumAssertResult): VerifyPurchaseResult['ok'] extends true ? never : VerifyPurchaseResult {
  if (r.kind === 'valid') return { ok: true, plan: 'pro', entitled: true } as never;
  if (r.kind === 'pending') return { ok: false, reason: 'pending' };
  if (r.kind === 'transient' || r.kind === 'misconfigured') return { ok: false, reason: r.kind };
  return { ok: false, reason: 'invalid' };
}

export async function verifyAndBindPurchase(input: VerifyPurchaseInput): Promise<VerifyPurchaseResult> {
  const deviceId = sanitizeDeviceId(input.deviceId);
  if (!deviceId || !input.productId?.trim() || !input.purchaseToken?.trim()) {
    return { ok: false, reason: 'bad_input' };
  }

  const plan = planFromProductId(input.productId.trim());
  if (plan === 'free') {
    return { ok: false, reason: 'invalid' };
  }

  const source = input.source ?? 'google_play';
  const assertResult = await assertPremiumPurchase(
    input.productId.trim(),
    input.purchaseToken.trim(),
    source === 'app_store' ? 'app_store' : undefined,
  );

  if (assertResult.kind !== 'valid') {
    return mapAssert(assertResult) as VerifyPurchaseResult;
  }

  const bind = await assertPurchaseBindAllowed(
    deviceId,
    input.purchaseToken.trim(),
    input.originalTransactionId,
  );
  if (!bind.ok) {
    return { ok: false, reason: 'invalid' };
  }

  const { userId } = await ensureUserForDevice(deviceId, {
    platform: input.platform,
    appVersion: input.appVersion,
  });

  const expiresAt =
    input.expiresAt ??
    (assertResult.kind === 'valid' ? assertResult.expiresAt ?? null : null);

  const stored: Omit<StoredEntitlement, 'registeredAt' | 'lastVerifiedAt'> = {
    userId,
    deviceId,
    productId: input.productId.trim(),
    purchaseToken: input.purchaseToken.trim(),
    source: plan === 'lifetime' ? 'lifetime' : source,
    plan,
    status: 'active',
    expiresAt,
    originalTransactionId: input.originalTransactionId ?? null,
  };

  await saveStoredEntitlement(stored);
  await bindPurchaseToDevice(deviceId, input.purchaseToken.trim(), input.originalTransactionId);

  return { ok: true, plan, entitled: true };
}
