import type { ComponentProps } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { AppListItem } from '../../../components/ui/AppListItem';

type Props = {
  icon: ComponentProps<typeof Ionicons>['name'];
  label: string;
  subtitle?: string;
  badge?: string;
  showDivider?: boolean;
  onPress?: () => void;
};

/** Diia-style settings row — theme-aware via AppListItem. */
export function ProfileSettingRow(props: Props) {
  return <AppListItem {...props} />;
}
