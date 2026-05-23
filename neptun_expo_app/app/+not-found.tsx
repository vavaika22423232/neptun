import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { PrimaryButton } from '../src/components/PrimaryButton';
import { Text } from '../src/components/Text';
import { navigateToHref } from '../src/core/navigation/navigate';

export default function NotFoundScreen() {
  const router = useRouter();

  return (
    <View style={styles.root}>
      <Text title>Сторінку не знайдено</Text>
      <Text muted style={styles.sub}>
        Посилання застаріло або некоректне.
      </Text>
      <PrimaryButton onPress={() => navigateToHref('/(tabs)', { replace: true })}>На головну</PrimaryButton>
      <PrimaryButton onPress={() => router.back()}>Назад</PrimaryButton>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: 'center', padding: 24, gap: 12 },
  sub: { textAlign: 'center', marginBottom: 8 },
});
