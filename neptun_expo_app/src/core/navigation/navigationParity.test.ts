/**
 * Parity tests ported from Flutter `test/push_deep_link_test.dart` and `app_router_redirect_test.dart`.
 * Run: npx tsx src/core/navigation/navigationParity.test.ts
 */
import assert from 'node:assert/strict';
import { resolveAppRedirect } from './appRedirect';
import { redirectFromWidgetUri, routeFromPushData } from './pushDeepLink';
import { RoutePaths } from './routePaths';

function run(name: string, fn: () => void) {
  try {
    fn();
    console.log(`ok ${name}`);
  } catch (e) {
    console.error(`FAIL ${name}`);
    throw e;
  }
}

run('open_chat → chat', () => {
  assert.equal(routeFromPushData({ action: 'open_chat' }), RoutePaths.chat);
});

run('type radar → radar', () => {
  assert.equal(routeFromPushData({ type: 'radar' }), RoutePaths.radar);
});

run('regions → alerts', () => {
  assert.equal(routeFromPushData({ action: 'regions' }), RoutePaths.alerts);
});

run('track_id → home', () => {
  assert.equal(routeFromPushData({ track_id: 'abc' }), RoutePaths.home);
});

run('neptun://alarm?open=radar', () => {
  assert.equal(redirectFromWidgetUri('neptun://alarm?open=radar'), RoutePaths.radar);
});

run('first launch → onboarding', () => {
  assert.equal(
    resolveAppRedirect({ isFirstLaunch: true, location: '/', uri: '' }),
    RoutePaths.onboarding,
  );
});

run('completed onboarding → home', () => {
  assert.equal(
    resolveAppRedirect({ isFirstLaunch: false, location: RoutePaths.onboarding, uri: '' }),
    RoutePaths.home,
  );
});

run('/regions legacy → alerts', () => {
  assert.equal(
    resolveAppRedirect({ isFirstLaunch: false, location: '/regions', uri: '' }),
    RoutePaths.alerts,
  );
});

console.log('navigation parity: all passed');
