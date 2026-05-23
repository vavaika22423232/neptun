import type { ComponentProps } from 'react';
import { PrimaryButton } from '../PrimaryButton';

type Props = ComponentProps<typeof PrimaryButton>;

/** Primary CTA — wraps existing PrimaryButton for design-system consistency. */
export function AppButton(props: Props) {
  return <PrimaryButton {...props} />;
}
