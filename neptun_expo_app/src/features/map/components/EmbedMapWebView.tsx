import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  LayoutChangeEvent,
  Platform,
  StyleSheet,
  View,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { Text } from '../../../components/Text';
import { moderatorService } from '../../../services/moderatorService';
import { fonts } from '../../../theme/fonts';
import { useLegacyColors, useThemedStyles } from '../../../theme/useAppTheme';
import {
  MAP_EMBED_URL,
  MAP_WEBVIEW_IOS_MOUNT_DELAY_MS,
  MAP_WEBVIEW_LOAD_TIMEOUT_MS,
  MAP_WEBVIEW_MIN_HEIGHT,
} from '../constants/mapEmbed';
import { useMapWebViewRecovery } from '../hooks/useMapWebViewRecovery';
import { useMapStore } from '../state/mapStore';
import {
  buildMapBridgeAndRecoverScript,
  MAP_EMBED_BEFORE_LOAD,
  MAP_WEBVIEW_USER_AGENT,
} from '../utils/mapWebViewInject';
import { MapWebViewErrorPanel } from './MapWebViewErrorPanel';

type Props = {
  onThreatMarkerTap: (marker: Record<string, unknown>) => void;
};

/**
 * Production map WebView — Flutter `MapTab`.
 * - Always `MAP_EMBED_URL` (moderator secret injected after load, not bootstrap URL).
 * - No error on tile/CDN 404; full-screen error only after load timeout.
 */
export function EmbedMapWebView({ onThreatMarkerTap }: Props) {
  const c = useLegacyColors();
  const styles = useEmbedStyles();
  const webRef = useRef<WebView>(null);
  const [layout, setLayout] = useState({ width: 0, height: 0 });
  const [iosMountReady, setIosMountReady] = useState(Platform.OS !== 'ios');
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const mapReadyRef = useRef(false);
  const loadTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recoverTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const dismissLoading = useCallback(() => {
    setLoading(false);
    if (loadTimeoutRef.current) {
      clearTimeout(loadTimeoutRef.current);
      loadTimeoutRef.current = null;
    }
  }, []);

  const clearRecoverTimers = useCallback(() => {
    for (const t of recoverTimersRef.current) clearTimeout(t);
    recoverTimersRef.current = [];
  }, []);

  const injectRecover = useCallback(async () => {
    const secret = await moderatorService.getSecret();
    webRef.current?.injectJavaScript(buildMapBridgeAndRecoverScript(secret));
  }, []);

  const scheduleRecoverKicks = useCallback(() => {
    clearRecoverTimers();
    void injectRecover();
    for (const ms of [0, 120, 320, 900, 1500, 2400, 4000, 6000]) {
      recoverTimersRef.current.push(setTimeout(() => void injectRecover(), ms));
    }
  }, [clearRecoverTimers, injectRecover]);

  useMapWebViewRecovery(scheduleRecoverKicks);

  const armLoadTimeout = useCallback(() => {
    if (loadTimeoutRef.current) clearTimeout(loadTimeoutRef.current);
    loadTimeoutRef.current = setTimeout(() => {
      if (!mapReadyRef.current) {
        setLoadFailed(true);
        dismissLoading();
      }
    }, MAP_WEBVIEW_LOAD_TIMEOUT_MS);
  }, [dismissLoading]);

  const reloadMap = useCallback(() => {
    mapReadyRef.current = false;
    setLoadFailed(false);
    setLoading(true);
    armLoadTimeout();
    if (webRef.current) webRef.current.reload();
    else scheduleRecoverKicks();
  }, [armLoadTimeout, scheduleRecoverKicks]);

  useEffect(() => {
    if (Platform.OS === 'ios') {
      const t = setTimeout(() => setIosMountReady(true), MAP_WEBVIEW_IOS_MOUNT_DELAY_MS);
      return () => clearTimeout(t);
    }
    return undefined;
  }, []);

  useEffect(() => {
    armLoadTimeout();
    return () => {
      if (loadTimeoutRef.current) clearTimeout(loadTimeoutRef.current);
      clearRecoverTimers();
    };
  }, [armLoadTimeout, clearRecoverTimers]);

  const locateUserNonce = useMapStore((s) => s.locateUserNonce);
  const focusPlace = useMapStore((s) => s.focusPlace);

  useEffect(() => {
    if (locateUserNonce <= 0) return;
    webRef.current?.injectJavaScript(`
      try {
        window.dispatchEvent(new Event('neptun:locate-user'));
        if (typeof window.__neptunLocateUser === 'function') window.__neptunLocateUser();
      } catch (e) {}
      true;
    `);
  }, [locateUserNonce]);

  useEffect(() => {
    if (!focusPlace) return;
    const detail = JSON.stringify({
      lat: focusPlace.lat,
      lng: focusPlace.lng,
      zoom: focusPlace.zoom,
      duration: focusPlace.duration,
      label: focusPlace.label,
    });
    webRef.current?.injectJavaScript(`
      try {
        window.dispatchEvent(new CustomEvent('neptun:map-goto', { detail: ${detail} }));
      } catch (e) {}
      true;
    `);
  }, [focusPlace]);

  useEffect(() => {
    return moderatorService.subscribe(() => {
      void injectRecover();
    });
  }, [injectRecover]);

  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    if (width < 50 || height < MAP_WEBVIEW_MIN_HEIGHT) return;
    setLayout((prev) => {
      if (Math.abs(prev.width - width) < 2 && Math.abs(prev.height - height) < 2) return prev;
      return { width, height };
    });
  }, []);

  const layoutReady = layout.width >= 50 && layout.height >= MAP_WEBVIEW_MIN_HEIGHT;
  const canRenderWebView = layoutReady && iosMountReady;

  const onMessage = useCallback(
    (raw: string) => {
      try {
        const decoded = JSON.parse(raw) as {
          type?: string;
          marker?: Record<string, unknown>;
        };
        if (decoded.type === 'neptun_map_ready') {
          mapReadyRef.current = true;
          setLoadFailed(false);
          dismissLoading();
          return;
        }
        if (decoded.type === 'threat_marker_tap' && decoded.marker) {
          onThreatMarkerTap(decoded.marker);
        }
      } catch {
        /* ignore */
      }
    },
    [dismissLoading, onThreatMarkerTap],
  );

  return (
    <View style={styles.root} onLayout={onLayout} collapsable={false}>
      {canRenderWebView ? (
        <WebView
          ref={webRef}
          source={{ uri: MAP_EMBED_URL }}
          style={[styles.webview, { width: layout.width, height: layout.height }]}
          containerStyle={{ width: layout.width, height: layout.height }}
          userAgent={MAP_WEBVIEW_USER_AGENT}
          applicationNameForUserAgent="NeptunAlarmApp/2.1"
          injectedJavaScriptBeforeContentLoaded={MAP_EMBED_BEFORE_LOAD}
          javaScriptEnabled
          domStorageEnabled
          sharedCookiesEnabled
          thirdPartyCookiesEnabled
          cacheEnabled
          allowsInlineMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          scrollEnabled={false}
          bounces={false}
          allowsBackForwardNavigationGestures={false}
          originWhitelist={['https://*']}
          setSupportMultipleWindows={false}
          webviewDebuggingEnabled={__DEV__}
          onMessage={(e) => onMessage(e.nativeEvent.data)}
          onLoadStart={() => {
            mapReadyRef.current = false;
            setLoadFailed(false);
            setLoading(true);
            armLoadTimeout();
          }}
          onLoadProgress={({ nativeEvent }) => {
            if (nativeEvent.progress >= 0.6) dismissLoading();
          }}
          onLoadEnd={() => {
            dismissLoading();
            scheduleRecoverKicks();
          }}
          onContentProcessDidTerminate={() => {
            reloadMap();
          }}
          {...(Platform.OS === 'android'
            ? { androidLayerType: 'hardware' as const, nestedScrollEnabled: true }
            : {})}
        />
      ) : (
        <View style={styles.centered}>
          <ActivityIndicator color={c.accent} />
          <Text muted style={styles.loadingText}>
            {!iosMountReady ? 'Ініціалізація…' : 'Розмір екрана…'}
          </Text>
        </View>
      )}

      {loading ? (
        <View style={styles.loadingOverlay} pointerEvents="none">
          <ActivityIndicator size="large" color={c.accent} />
          <Text muted style={styles.loadingText}>
            Завантаження карти...
          </Text>
        </View>
      ) : null}

      {loadFailed && !loading ? <MapWebViewErrorPanel onRetry={reloadMap} /> : null}
    </View>
  );
}

function useEmbedStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: t.legacyColors.bg2,
        overflow: 'hidden',
      },
      webview: {
        backgroundColor: t.legacyColors.bg2,
      },
      centered: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.legacyColors.bg2,
        gap: 10,
      },
      loadingOverlay: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: t.legacyColors.bg,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        zIndex: 10,
      },
      loadingText: {
        marginTop: 8,
        fontFamily: fonts.medium,
        fontSize: 14,
      },
    }),
  );
}
