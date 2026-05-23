import { memo, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { profileTokens } from '../profileTokens';

type Props = {
  children: ReactNode;
};

/** Groups status + PRO cards as the profile control-center header. */
function ProfileHeroStackInner({ children }: Props) {
  return <View style={styles.stack}>{children}</View>;
}

const styles = StyleSheet.create({
  stack: {
    gap: profileTokens.heroGap,
  },
});

export const ProfileHeroStack = memo(ProfileHeroStackInner);
