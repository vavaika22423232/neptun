/** Map onboarding short labels → `PrefsKeys.selectedRegions` full names */
export function onboardingRegionToFullName(short: string): string {
  if (short === 'м. Київ') return 'м. Київ';
  return `${short} область`;
}

export function fullNamesFromOnboardingSelection(selected: Set<string>): string[] {
  return [...selected].map(onboardingRegionToFullName);
}
