import type { ComponentProps } from 'react';
import { NeptunEmptyState } from '../../design/components/NeptunEmptyState';

type Props = ComponentProps<typeof NeptunEmptyState>;

export function AppEmptyState(props: Props) {
  return <NeptunEmptyState {...props} />;
}
