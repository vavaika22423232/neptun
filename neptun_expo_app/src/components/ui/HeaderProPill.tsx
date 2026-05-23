import { memo } from 'react';
import { HeaderActionButton } from './HeaderActionButton';

type Props = {
  isPremium?: boolean;
  onPress?: () => void;
  compact?: boolean;
};

export const HeaderProPill = memo(function HeaderProPill({ isPremium, onPress, compact }: Props) {
  return (
    <HeaderActionButton
      icon={isPremium ? 'star' : 'ribbon-outline'}
      label="PRO"
      tone="premium"
      accessibilityLabel="Преміум"
      onPress={onPress}
      compact={compact}
    />
  );
});
