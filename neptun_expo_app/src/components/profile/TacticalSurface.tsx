import type { ComponentProps } from 'react';
import { NeptunSurface } from '../../design/components/NeptunSurface';

type Props = ComponentProps<typeof NeptunSurface>;

/** @deprecated Use `NeptunSurface` from `src/design` */
export function TacticalSurface(props: Props) {
  return <NeptunSurface {...props} />;
}
