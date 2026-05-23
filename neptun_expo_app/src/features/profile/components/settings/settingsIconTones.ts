import type { ComponentProps } from 'react';
import type { Ionicons } from '@expo/vector-icons';
import type { ResolvedScheme } from '../../../../theme/types';
import { neptunPalette as p } from '../../../../theme/neptunPalette';

/** iOS-style colored icon circle tones — same hues in light & dark. */
export type SettingsIconTone =
  | 'blue'
  | 'purple'
  | 'green'
  | 'orange'
  | 'pink'
  | 'red'
  | 'teal'
  | 'indigo'
  | 'gray'
  | 'gold'
  /** @deprecated use tone names above */
  | 'steel'
  | 'cool'
  | 'muted'
  | 'pro'
  | 'soft'
  | 'deep';

type IconColors = { background: string; foreground: string };

const ICON_TONES: Record<
  'blue' | 'purple' | 'green' | 'orange' | 'pink' | 'red' | 'teal' | 'indigo' | 'gray' | 'gold',
  IconColors
> = {
  blue: { background: p.iosBlue, foreground: '#FFFFFF' },
  purple: { background: p.iosPurple, foreground: '#FFFFFF' },
  green: { background: p.iosGreen, foreground: '#FFFFFF' },
  orange: { background: p.iosOrange, foreground: '#FFFFFF' },
  pink: { background: p.iosPink, foreground: '#FFFFFF' },
  red: { background: p.iosRed, foreground: '#FFFFFF' },
  teal: { background: p.iosTeal, foreground: '#FFFFFF' },
  indigo: { background: p.iosIndigo, foreground: '#FFFFFF' },
  gray: { background: p.iosGray, foreground: '#FFFFFF' },
  gold: { background: '#FFCC00', foreground: '#FFFFFF' },
};

const LEGACY_TONE_MAP: Record<string, keyof typeof ICON_TONES> = {
  steel: 'blue',
  teal: 'teal',
  cool: 'teal',
  muted: 'gray',
  pro: 'gold',
  soft: 'gray',
  deep: 'indigo',
};

type IonName = ComponentProps<typeof Ionicons>['name'];

export const SETTINGS_ICON_TONE_BY_NAME: Partial<Record<IonName, SettingsIconTone>> = {
  'map-outline': 'blue',
  'location-outline': 'blue',
  'options-outline': 'gold',
  'moon-outline': 'indigo',
  'notifications-outline': 'red',
  'alert-circle-outline': 'orange',
  'volume-high-outline': 'pink',
  'phone-portrait-outline': 'gray',
  'megaphone-outline': 'purple',
  'battery-charging-outline': 'green',
  'paper-plane-outline': 'teal',
  'newspaper-outline': 'orange',
  'time-outline': 'indigo',
  'stats-chart-outline': 'gold',
  'flame-outline': 'orange',
  'shield-checkmark-outline': 'green',
  'navigate-outline': 'blue',
  'chatbox-ellipses-outline': 'purple',
  'heart-outline': 'pink',
  'document-text-outline': 'gray',
  'reader-outline': 'gray',
  'globe-outline': 'teal',
  'information-circle-outline': 'gray',
  'shield-outline': 'gold',
  'grid-outline': 'indigo',
  'flag-outline': 'red',
  'cloud-outline': 'teal',
  'albums-outline': 'blue',
  'color-palette-outline': 'purple',
  'language-outline': 'blue',
};

function normalizeTone(tone: SettingsIconTone): keyof typeof ICON_TONES {
  if (tone in ICON_TONES) return tone as keyof typeof ICON_TONES;
  return LEGACY_TONE_MAP[tone] ?? 'blue';
}

export function getSettingsIconToneColors(
  _scheme: ResolvedScheme,
  tone: SettingsIconTone,
): IconColors {
  return ICON_TONES[normalizeTone(tone)];
}

export function resolveSettingsIconTone(
  icon: IonName,
  explicit?: SettingsIconTone,
): SettingsIconTone {
  return explicit ?? SETTINGS_ICON_TONE_BY_NAME[icon] ?? 'blue';
}
