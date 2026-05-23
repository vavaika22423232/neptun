export function formatRelativeTime(ts: number | null): string {
  if (ts == null) return 'оновлення —';
  const diff = Date.now() - ts;
  if (diff < 50_000) return 'щойно';
  if (diff < 3_600_000) return `оновлено ${Math.floor(diff / 60_000)} хв тому`;
  if (diff < 86_400_000) return `оновлено ${Math.floor(diff / 3_600_000)} год тому`;
  const d = new Date(ts);
  return `оновлено ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

export function formatFetchedShort(ts: number | null): string {
  if (ts == null) return '—';
  const diff = Date.now() - ts;
  if (diff < 45_000) return 'щойно';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} хв`;
  return `${Math.floor(diff / 3_600_000)} год`;
}
