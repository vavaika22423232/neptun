/** Flutter `BriefingPage._safetyTips`. */
export const BRIEFING_SAFETY_TIPS = [
  'Тримайте документи та аптечку поруч',
  'Знайте найближче укриття',
  'У тривогу — негайно в укриття',
  'Не використовуйте ліфт під час тривоги',
  'Майте заряджений телефон та powerbank',
] as const;

export function randomSafetyTip(): string {
  const i = Math.floor(Math.random() * BRIEFING_SAFETY_TIPS.length);
  return BRIEFING_SAFETY_TIPS[i] ?? BRIEFING_SAFETY_TIPS[0];
}
