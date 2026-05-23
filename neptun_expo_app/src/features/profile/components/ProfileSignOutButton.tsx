import { Alert, StyleSheet } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { authService } from '../../../services/authService';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  onSignedOut: () => void;
};

export function ProfileSignOutButton({ onSignedOut }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      btn: {
        borderRadius: t.profile.radiusCard,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.danger + '33',
        backgroundColor: t.colors.dangerMuted,
        paddingVertical: 15,
        alignItems: 'center',
      },
      label: {
        fontFamily: fonts.semiBold,
        fontSize: 15,
        color: t.colors.danger,
      },
    }),
  );

  const confirm = () => {
    Alert.alert(
      'Вийти з сесії',
      'Буде скинуто токен чату на цьому пристрої. Налаштування тривог залишаться.',
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Вийти',
          style: 'destructive',
          onPress: () => {
            void authService.logout().then(() => onSignedOut());
          },
        },
      ],
    );
  };

  return (
    <Animated.View entering={FadeInDown.delay(300).duration(320)}>
      <NeptunPressable onPress={confirm} style={styles.btn} accessibilityLabel="Вийти з сесії чату">
        <Text style={styles.label}>Вийти з сесії</Text>
      </NeptunPressable>
    </Animated.View>
  );
}
