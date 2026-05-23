/** Ukrainian copy for selected region count (profile + regions chrome). */
export function regionSelectionLabel(count: number): string {
  if (count === 0) return 'Оберіть області та міста';
  if (count === 1) return '1 регіон обрано';
  if (count < 5) return `${count} регіони обрано`;
  return `${count} регіонів обрано`;
}
