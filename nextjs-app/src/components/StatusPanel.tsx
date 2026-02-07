'use client';

interface StatusPanelProps {
  alarmCount: number;
  lastUpdate: Date | null;
  error: string | null;
}

export default function StatusPanel({ alarmCount, lastUpdate, error }: StatusPanelProps) {
  const getUpdateText = () => {
    if (error) return 'Не вдалося завантажити';
    if (!lastUpdate) return 'Завантаження...';
    return `Оновлено: ${lastUpdate.toLocaleTimeString('uk-UA')}`;
  };

  const getUpdateClass = () => {
    if (error) return 'text-red-400';
    if (!lastUpdate) return 'text-white/50';
    const secondsAgo = (Date.now() - lastUpdate.getTime()) / 1000;
    if (secondsAgo > 120) return 'text-yellow-400';
    return 'text-white/50';
  };

  return (
    <div className="fixed top-14 sm:top-16 left-3 sm:left-5 bg-[#2c2c2e]/90 backdrop-blur-sm border border-white/10 rounded-xl sm:rounded-2xl px-3 sm:px-5 py-2.5 sm:py-4 z-[1000] min-w-[100px] sm:min-w-[140px]">
      <h3 className="text-[8px] sm:text-[10px] font-medium text-white/50 uppercase tracking-wider mb-1 sm:mb-2">
        Тривоги
      </h3>
      <div
        className={`text-2xl sm:text-4xl font-medium leading-none ${
          alarmCount > 0 ? 'text-white' : 'text-white/50'
        }`}
      >
        {alarmCount}
      </div>
      <div className={`text-[9px] sm:text-[11px] mt-1.5 sm:mt-2.5 font-light ${getUpdateClass()}`}>
        {getUpdateText()}
      </div>
    </div>
  );
}
