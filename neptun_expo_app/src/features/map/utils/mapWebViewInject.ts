/** After WebView load — MapLibre needs resize kicks (see nextjs map-lifecycle-recovery.ts). */
export const MAP_WEBVIEW_USER_AGENT =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like MacOS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 NeptunAlarmApp/2.1 wv';

/** Runs before HTML paint — same flags as nextjs layout inline script for `?embed=1`. */
export const MAP_EMBED_BEFORE_LOAD = `
document.documentElement.classList.add('embed-mode');
true;
`;

export function buildMapBridgeAndRecoverScript(adminSecret?: string | null): string {
  const adminLine = adminSecret
    ? `window.__ADMIN_SECRET = decodeURIComponent("${encodeURIComponent(adminSecret)}");`
    : '';
  return `
(function() {
  if (!window.__NEPTUN_RN_BRIDGE__) {
    window.__NEPTUN_RN_BRIDGE__ = true;
    document.documentElement.classList.add('embed-mode');
    window.NeptunApp = {
      postMessage: function(message) {
        if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
          window.ReactNativeWebView.postMessage(message);
        }
      }
    };
  }
  ${adminLine}
  function kick() {
    try { window.dispatchEvent(new Event('resize')); } catch (e) {}
    try { window.dispatchEvent(new Event('neptun:map-recover')); } catch (e) {}
    if (typeof window.__neptunRecoverMap === 'function') window.__neptunRecoverMap();
  }
  kick();
  [0, 120, 320, 900, 1500, 2400].forEach(function(ms) { setTimeout(kick, ms); });
  if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
    window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'neptun_map_ready' }));
  }
})();
true;
`;
}
