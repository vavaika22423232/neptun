import { createElement, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { moderatorService } from '../../../services/moderatorService';
import { colors } from '../../../theme/colors';
import { fonts } from '../../../theme/fonts';
import { useLegacyScreenStyles } from '../../../theme/useLegacyScreenStyles';
import { useMapStore } from '../state/mapStore';

type Props = {
  onThreatMarkerTap: (marker: Record<string, unknown>) => void;
};

/**
 * Expo web: iframe `/?embed=1` (same as Flutter / iOS WebView).
 * Requires CSP `frame-ancestors` for embed on neptun.in.ua (see nextjs-app/next.config.ts).
 */
export function EmbedMapWebView({ onThreatMarkerTap }: Props) {
  const styles = useScreenStyles();
const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const dismissed = useRef(false);
  const focusPlace = useMapStore((s) => s.focusPlace);

  useEffect(() => {
    void (async () => {
      const mapUrl = moderatorService.buildMapUrl('dark');
      const secret = await moderatorService.getSecret();
      const isMod = await moderatorService.isModerator();
      if (isMod && secret) {
        setUri(moderatorService.buildModeratorBootstrapUrl(mapUrl, secret));
      } else {
        setUri(mapUrl);
      }
    })();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      dismissed.current = true;
      setLoading(false);
    }, 5000);
    return () => clearTimeout(t);
  }, [uri]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        if (data?.type === 'threat_marker_tap' && data.marker) {
          onThreatMarkerTap(data.marker as Record<string, unknown>);
        }
      } catch {
        /* ignore */
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [onThreatMarkerTap]);

  useEffect(() => {
    if (!focusPlace) return;
    iframeRef.current?.contentWindow?.postMessage(
      {
        type: 'neptun_map_goto',
        detail: {
          lat: focusPlace.lat,
          lng: focusPlace.lng,
          zoom: focusPlace.zoom,
          duration: focusPlace.duration,
          label: focusPlace.label,
        },
      },
      '*',
    );
  }, [focusPlace]);

  if (!uri) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      {createElement('iframe', {
        ref: iframeRef,
        title: 'NEPTUN Map',
        src: uri,
        style: {
          border: 'none',
          width: '100%',
          height: '100%',
          flex: 1,
          display: 'block',
          backgroundColor: colors.bg,
        },
        onLoad: () => {
          dismissed.current = true;
          setLoading(false);
        },
      })}
      {loading ? (
        <View style={styles.overlay} pointerEvents="none">
          <ActivityIndicator size="large" color={colors.accent} />
          <Text muted style={styles.loadingText}>
            Завантаження карти...
          </Text>
        </View>
      ) : null}
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: { flex: 1, minHeight: 400, backgroundColor: c.bg },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: c.bg,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: c.bg,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  loadingText: { fontFamily: fonts.medium, fontSize: 14 },
}));
}
