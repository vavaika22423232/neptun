import { NextResponse } from 'next/server';
import { resolveEntitlementsForDevice, sanitizeDeviceId } from './entitlement-store';
import type { EntitlementFeatures, PlanId } from './plans';
import { PLAN_RANK } from './plans';
import { requireDeviceAuth, type DeviceAuthResult } from '../device-auth';

export async function requireAuthenticatedDevice(
  request: Request,
  deviceId: string | null,
): Promise<
  | { ok: true; deviceId: string }
  | { ok: false; status: number; error: string }
> {
  const auth: DeviceAuthResult = requireDeviceAuth(request, deviceId);
  if (!auth.ok) {
    const status = auth.response.status;
    return { ok: false, status, error: status === 401 ? 'auth_required' : 'device_mismatch' };
  }
  return { ok: true, deviceId: auth.deviceId };
}

export async function requireMinPlan(
  request: Request,
  deviceId: string | null,
  minPlan: PlanId,
): Promise<
  | { ok: true; plan: PlanId; features: EntitlementFeatures; deviceId: string }
  | { ok: false; status: number; error: string }
> {
  const auth = await requireAuthenticatedDevice(request, deviceId);
  if (!auth.ok) {
    return auth;
  }

  const ent = await resolveEntitlementsForDevice(auth.deviceId);
  if (PLAN_RANK[ent.plan] < PLAN_RANK[minPlan]) {
    return { ok: false, status: 403, error: 'plan_required' };
  }
  return { ok: true, plan: ent.plan, features: ent.features, deviceId: auth.deviceId };
}

/** @deprecated use requireMinPlan(request, deviceId, minPlan) */
export async function requireMinPlanLegacy(
  deviceId: string | null,
  minPlan: PlanId,
): Promise<{ ok: true; plan: PlanId; features: EntitlementFeatures } | { ok: false; status: number; error: string }> {
  const id = sanitizeDeviceId(deviceId);
  if (!id) {
    return { ok: false, status: 401, error: 'device_required' };
  }
  const ent = await resolveEntitlementsForDevice(id);
  if (PLAN_RANK[ent.plan] < PLAN_RANK[minPlan]) {
    return { ok: false, status: 403, error: 'plan_required' };
  }
  return { ok: true, plan: ent.plan, features: ent.features };
}

export function historyCutoffIso(historyDays: number): string {
  const ms = historyDays * 24 * 60 * 60 * 1000;
  return new Date(Date.now() - ms).toISOString();
}
