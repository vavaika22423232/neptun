import type { Alarm } from '@/types';
import { normalizeAlarmRegionName } from '@/lib/map/alarm-hasc-filter';

/** True if any active oblast-level alarm matches this place's oblast HASC or label. */
export function isPlaceOblastInAlarm(
  alarms: Alarm[],
  oblastHasc: string | undefined,
  subtitle: string,
): boolean {
  const subNorm = normalizeAlarmRegionName(subtitle);
  for (const alarm of alarms) {
    if (alarm.regionType !== 'State' || !alarm.activeAlerts?.length) continue;
    const rname = normalizeAlarmRegionName(alarm.regionName || '');
    if (!rname) continue;
    if (subNorm && (subNorm.includes(rname) || rname.includes(subNorm.split(' ')[0] || ''))) {
      return true;
    }
    const rid = String(alarm.regionId || '').toUpperCase();
    if (oblastHasc && rid) {
      const tail = oblastHasc.split('.')[1]?.toUpperCase();
      if (tail && (`UA-${tail}` === rid || oblastHasc === rid)) return true;
    }
  }
  return false;
}
