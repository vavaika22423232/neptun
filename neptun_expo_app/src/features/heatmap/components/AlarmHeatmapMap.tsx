import { useMemo } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';
import { heatmapMaxCount, heatmapOblastFillColor } from '../logic/heatmapColors';
import { getOblastCentroidsByStateId } from '../utils/oblastCentroids';

type Props = {
  countsByStateId: Record<string, number>;
  isDark?: boolean;
};

function buildHeatmapHtml(counts: Record<string, number>, isDark: boolean): string {
  const centroids = getOblastCentroidsByStateId();
  const maxC = heatmapMaxCount(counts);
  const circles: { lat: number; lng: number; radius: number; color: string; opacity: number }[] = [];

  if (maxC > 0) {
    for (const [id, [lng, lat]] of Object.entries(centroids)) {
      const n = counts[id] ?? 0;
      if (n <= 0) continue;
      const t = Math.sqrt(n / maxC);
      const radiusM = 28000 + 125000 * t;
      const { fill, fillOpacity } = heatmapOblastFillColor(id, counts, isDark);
      circles.push({ lat, lng, radius: radiusM, color: fill, opacity: fillOpacity });
    }
  }

  const tileUrl = isDark
    ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'
    : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png';

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map { margin:0; padding:0; width:100%; height:100%; background:${isDark ? '#141414' : '#f3f4f6'}; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const circles = ${JSON.stringify(circles)};
    const map = L.map('map', {
      center: [48.5, 31.5],
      zoom: 6,
      minZoom: 4,
      maxZoom: 11,
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer('${tileUrl}', { subdomains: 'abcd', maxZoom: 11 }).addTo(map);
    map.setMaxBounds([[44, 20], [53, 42]]);
    for (const c of circles) {
      L.circle([c.lat, c.lng], {
        radius: c.radius,
        color: c.color,
        fillColor: c.color,
        fillOpacity: c.opacity,
        weight: 0,
      }).addTo(map);
    }
  </script>
</body>
</html>`;
}

/** Flutter `AlarmHeatmapMapView` — Leaflet circles on Carto dark tiles (WebView). */
export function AlarmHeatmapMap({ countsByStateId, isDark = true }: Props) {
  const html = useMemo(
    () => buildHeatmapHtml(countsByStateId, isDark),
    [countsByStateId, isDark],
  );

  return (
    <View style={styles.root}>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        style={styles.web}
        scrollEnabled={false}
        bounces={false}
        overScrollMode="never"
        setBuiltInZoomControls={Platform.OS === 'android'}
        javaScriptEnabled
        domStorageEnabled
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, overflow: 'hidden', borderRadius: 12 },
  web: { flex: 1, backgroundColor: '#141414' },
});
