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
    <div className="fixed top-20 left-5 bg-[#2c2c2e] border border-white/10 rounded-2xl px-5 py-4 z-[1000] min-w-[140px]">
      <h3 className="text-[10px] font-medium text-white/50 uppercase tracking-wider mb-2">
        Тривоги
      </h3>
      <div
        className={`text-4xl font-medium leading-none ${
          alarmCount > 0 ? 'text-white' : 'text-white/50'
        }`}
      >
        {alarmCount}
      </div>
      <div className={`text-[11px] mt-2.5 font-light ${getUpdateClass()}`}>
        {getUpdateText()}
      </div>
    </div>
  );
}
