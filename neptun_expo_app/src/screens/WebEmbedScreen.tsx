import { useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';
import WebView from 'react-native-webview';
import { useLegacyScreenStyles } from '../theme/useLegacyScreenStyles';

const ALLOWED_HOSTS = new Set(['neptun.in.ua', 'www.neptun.in.ua']);

function resolveEmbedUrl(raw?: string): string {
  const fallback = 'https://neptun.in.ua';
  if (!raw?.trim()) return fallback;
  try {
    const url = new URL(raw);
    if (url.protocol !== 'https:') return fallback;
    if (!ALLOWED_HOSTS.has(url.hostname.toLowerCase())) return fallback;
    return url.toString();
  } catch {
    return fallback;
  }
}

export function WebEmbedScreen() {
  const styles = useScreenStyles();
  const params = useLocalSearchParams<{ url?: string }>();
  const uri = resolveEmbedUrl(params.url);
  return (
    <View style={styles.root}>
      <WebView source={{ uri }} style={styles.web} />
    </View>
  );
}

function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
    root: { flex: 1, backgroundColor: c.bg },
    web: { flex: 1 },
  }));
}
