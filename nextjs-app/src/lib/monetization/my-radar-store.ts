import { getRedis } from '@/lib/redis';
import { randomUUID } from 'crypto';

export type MyRadarLocationRecord = {
  id: string;
  userId: string;
  label: string;
  type: 'home' | 'work' | 'family' | 'friend' | 'custom';
  regionId: string;
  cityId: string | null;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
};

const PREFIX = 'monetization:my_radar:';

function locKey(id: string) {
  return `${PREFIX}${id}`;
}

function userIndex(userId: string) {
  return `${PREFIX}user:${userId}`;
}

export async function listMyRadarLocations(userId: string): Promise<MyRadarLocationRecord[]> {
  const ids = await getRedis().smembers(userIndex(userId));
  const out: MyRadarLocationRecord[] = [];
  for (const id of ids) {
    const raw = await getRedis().hgetall(locKey(id));
    if (!raw?.id) continue;
    out.push({
      id: raw.id,
      userId: raw.userId,
      label: raw.label,
      type: (raw.type as MyRadarLocationRecord['type']) || 'custom',
      regionId: raw.regionId,
      cityId: raw.cityId || null,
      sortOrder: Number(raw.sortOrder || 0),
      createdAt: raw.createdAt,
      updatedAt: raw.updatedAt,
    });
  }
  return out.sort((a, b) => a.sortOrder - b.sortOrder);
}

export async function createMyRadarLocation(
  userId: string,
  data: Pick<MyRadarLocationRecord, 'label' | 'type' | 'regionId' | 'cityId' | 'sortOrder'>,
): Promise<MyRadarLocationRecord> {
  const id = randomUUID();
  const now = new Date().toISOString();
  const rec: MyRadarLocationRecord = { id, userId, ...data, createdAt: now, updatedAt: now };
  await getRedis().hset(locKey(id), {
    id: rec.id,
    userId: rec.userId,
    label: rec.label,
    type: rec.type,
    regionId: rec.regionId,
    cityId: rec.cityId ?? '',
    sortOrder: String(rec.sortOrder),
    createdAt: rec.createdAt,
    updatedAt: rec.updatedAt,
  });
  await getRedis().sadd(userIndex(userId), id);
  return rec;
}

export async function updateMyRadarLocation(
  id: string,
  userId: string,
  patch: Partial<Pick<MyRadarLocationRecord, 'label' | 'type' | 'regionId' | 'cityId' | 'sortOrder'>>,
): Promise<MyRadarLocationRecord | null> {
  const raw = await getRedis().hgetall(locKey(id));
  if (!raw?.id || raw.userId !== userId) return null;
  const now = new Date().toISOString();
  const next: MyRadarLocationRecord = {
    id: raw.id,
    userId: raw.userId,
    label: patch.label ?? raw.label,
    type: (patch.type ?? raw.type) as MyRadarLocationRecord['type'],
    regionId: patch.regionId ?? raw.regionId,
    cityId: patch.cityId !== undefined ? patch.cityId : raw.cityId || null,
    sortOrder: patch.sortOrder ?? Number(raw.sortOrder || 0),
    createdAt: raw.createdAt,
    updatedAt: now,
  };
  await getRedis().hset(locKey(id), {
    id: next.id,
    userId: next.userId,
    label: next.label,
    type: next.type,
    regionId: next.regionId,
    cityId: next.cityId ?? '',
    sortOrder: String(next.sortOrder),
    createdAt: next.createdAt,
    updatedAt: next.updatedAt,
  });
  return next;
}

export async function deleteMyRadarLocation(id: string, userId: string): Promise<boolean> {
  const raw = await getRedis().hgetall(locKey(id));
  if (!raw?.id || raw.userId !== userId) return false;
  await getRedis().del(locKey(id));
  await getRedis().srem(userIndex(userId), id);
  return true;
}
