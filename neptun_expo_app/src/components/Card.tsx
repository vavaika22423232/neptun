import type { ViewProps } from 'react-native';
import { AppCard } from './ui/AppCard';

/** @deprecated Prefer `AppCard` — kept for existing imports. */
export function Card(props: ViewProps) {
  return <AppCard {...props} />;
}
