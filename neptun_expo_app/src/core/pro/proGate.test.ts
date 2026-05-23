import assert from 'node:assert/strict';
import { isProFeatureUnlockedSync, ProFeature } from './proFeatureCatalog';

assert.equal(isProFeatureUnlockedSync(ProFeature.AlarmHistory, false), false);
assert.equal(isProFeatureUnlockedSync(ProFeature.AlarmHistory, true), true);
assert.equal(isProFeatureUnlockedSync(ProFeature.Trajectories, false), false);
assert.equal(isProFeatureUnlockedSync(ProFeature.ChatMedia, false), false);
console.log('proGate.test.ts: ok');
