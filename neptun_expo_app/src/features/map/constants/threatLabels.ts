export const threatTypeNames: Record<string, string> = {
  shahed: '🛩️ Шахеди/БПЛА',
  raketa: '🚀 Ракети',
  avia: '✈️ Авіація',
  artillery: '💥 Артилерія',
  obstril: '💥 Обстріл',
  fpv: '🎯 FPV дрони',
  pusk: '🚀 Пуски',
  kab: '💣 КАБи',
  rszv: '💣 РСЗВ',
  rozved: '🔍 Розвідники',
  vibuh: '💥 Вибухи',
  alarm: '🚨 Тривога',
  alarm_cancel: '✅ Відбій',
};

export function threatTypeColor(type: string): string {
  switch (type) {
    case 'shahed':
    case 'fpv':
    case 'rozved':
      return '#F59E0B';
    case 'raketa':
    case 'pusk':
    case 'kab':
    case 'rszv':
      return '#EF4444';
    case 'avia':
      return '#A78BFA';
    case 'artillery':
    case 'obstril':
    case 'vibuh':
      return '#F97316';
    case 'alarm':
      return '#FF3B30';
    case 'alarm_cancel':
      return '#34D399';
    default:
      return '#4CC9F0';
  }
}
