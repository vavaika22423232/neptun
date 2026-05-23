import { getRedis } from '@/lib/redis';
import { randomUUID } from 'crypto';

export type NotificationRuleRecord = {
  id: string;
  userId: string;
  enabled: boolean;
  regionIds: string[];
  cityIds: string[];
  threatTypes: string[];
  quietModeEnabled: boolean;
  quietModeStart: string | null;
  quietModeEnd: string | null;
  criticalOverrideEnabled: boolean;
  dedupeWindowMinutes: number;
  minSeverity: string | null;
  createdAt: string;
  updatedAt: string;
};

const INDEX_PREFIX = 'monetization:notification_rules:';

function ruleKey(id: string) {
  return `${INDEX_PREFIX}${id}`;
}

function userIndexKey(userId: string) {
  return `${INDEX_PREFIX}user:${userId}`;
}

export async function listNotificationRules(userId: string): Promise<NotificationRuleRecord[]> {
  const ids = await getRedis().smembers(userIndexKey(userId));
  const out: NotificationRuleRecord[] = [];
  for (const id of ids) {
    const raw = await getRedis().hgetall(ruleKey(id));
    if (!raw?.id) continue;
    out.push(parseRule(raw));
  }
  return out.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

function parseRule(raw: Record<string, string>): NotificationRuleRecord {
  return {
    id: raw.id,
    userId: raw.userId,
    enabled: raw.enabled === 'true',
    regionIds: JSON.parse(raw.regionIds || '[]') as string[],
    cityIds: JSON.parse(raw.cityIds || '[]') as string[],
    threatTypes: JSON.parse(raw.threatTypes || '[]') as string[],
    quietModeEnabled: raw.quietModeEnabled === 'true',
    quietModeStart: raw.quietModeStart || null,
    quietModeEnd: raw.quietModeEnd || null,
    criticalOverrideEnabled: raw.criticalOverrideEnabled !== 'false',
    dedupeWindowMinutes: Number(raw.dedupeWindowMinutes || 5),
    minSeverity: raw.minSeverity || null,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt,
  };
}

export async function createNotificationRule(
  userId: string,
  data: Partial<Omit<NotificationRuleRecord, 'id' | 'userId' | 'createdAt' | 'updatedAt'>>,
): Promise<NotificationRuleRecord> {
  const id = randomUUID();
  const now = new Date().toISOString();
  const rec: NotificationRuleRecord = {
    id,
    userId,
    enabled: data.enabled ?? true,
    regionIds: data.regionIds ?? [],
    cityIds: data.cityIds ?? [],
    threatTypes: data.threatTypes ?? [],
    quietModeEnabled: data.quietModeEnabled ?? false,
    quietModeStart: data.quietModeStart ?? null,
    quietModeEnd: data.quietModeEnd ?? null,
    criticalOverrideEnabled: data.criticalOverrideEnabled ?? true,
    dedupeWindowMinutes: data.dedupeWindowMinutes ?? 5,
    minSeverity: data.minSeverity ?? null,
    createdAt: now,
    updatedAt: now,
  };
  await persistRule(rec);
  await getRedis().sadd(userIndexKey(userId), id);
  return rec;
}

async function persistRule(rec: NotificationRuleRecord): Promise<void> {
  await getRedis().hset(ruleKey(rec.id), {
    id: rec.id,
    userId: rec.userId,
    enabled: String(rec.enabled),
    regionIds: JSON.stringify(rec.regionIds),
    cityIds: JSON.stringify(rec.cityIds),
    threatTypes: JSON.stringify(rec.threatTypes),
    quietModeEnabled: String(rec.quietModeEnabled),
    quietModeStart: rec.quietModeStart ?? '',
    quietModeEnd: rec.quietModeEnd ?? '',
    criticalOverrideEnabled: String(rec.criticalOverrideEnabled),
    dedupeWindowMinutes: String(rec.dedupeWindowMinutes),
    minSeverity: rec.minSeverity ?? '',
    createdAt: rec.createdAt,
    updatedAt: rec.updatedAt,
  });
}

export async function updateNotificationRule(
  id: string,
  userId: string,
  patch: Partial<NotificationRuleRecord>,
): Promise<NotificationRuleRecord | null> {
  const raw = await getRedis().hgetall(ruleKey(id));
  if (!raw?.id || raw.userId !== userId) return null;
  const current = parseRule(raw);
  const next = { ...current, ...patch, updatedAt: new Date().toISOString() };
  await persistRule(next);
  return next;
}

export async function deleteNotificationRule(id: string, userId: string): Promise<boolean> {
  const raw = await getRedis().hgetall(ruleKey(id));
  if (!raw?.id || raw.userId !== userId) return false;
  await getRedis().del(ruleKey(id));
  await getRedis().srem(userIndexKey(userId), id);
  return true;
}
