export const ALARM_SOUND_IDS = ['default', 'sharp', 'siren'] as const;
export type AlarmSoundId = (typeof ALARM_SOUND_IDS)[number];

export const ALARM_SOUND_LABELS: Record<AlarmSoundId, string> = {
  default: 'За замовчуванням',
  sharp: 'Різкий',
  siren: 'Сирена',
};
