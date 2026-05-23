import { memo } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { Text } from '../../../components/Text';
import { authService } from '../../../services/authService';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { profileTokens } from '../profileTokens';

type Props = {
  onSignedOut: () => void;
};

function ProfileLogoutButtonInner({ onSignedOut }: Props) {
  const styles = useLogoutStyles();

  const confirm = () => {
    Alert.alert(
      'Вийти з сесії',
      'Буде скинуто токен чату на цьому пристрої. Налаштування тривог залишаться.',
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Вийти',
          style: 'destructive',
          onPress: () => void authService.logout().then(onSignedOut),
        },
      ],
    );
  };

  return (
    <View style={styles.wrap}>
      <NeptunPressable onPress={confirm} style={styles.btn} accessibilityLabel="Вийти з сесії">
        <Text style={styles.label}>Вийти з сесії</Text>
      </NeptunPressable>
    </View>
  );
}

function useLogoutStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        marginHorizontal: profileTokens.insetH,
        marginTop: 4,
      },
      btn: {
        minHeight: 44,
        alignItems: 'center',
        justifyContent: 'center',
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 15,
        color: t.colors.danger,
      },
    }),
  );
}

export const ProfileLogoutButton = memo(ProfileLogoutButtonInner);
