import assert from 'node:assert/strict';
import { isThemeMode } from './themeMode';

assert.equal(isThemeMode('light'), true);
assert.equal(isThemeMode('dark'), true);
assert.equal(isThemeMode('system'), true);
assert.equal(isThemeMode('invalid'), false);
assert.equal(isThemeMode(undefined), false);
console.log('themeStorage.test.ts: ok');
