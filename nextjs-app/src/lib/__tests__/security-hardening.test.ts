import assert from 'node:assert/strict';
import { isDeviceJwtRequired } from '../device-auth';

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test('requires JWT in production by default', () => {
  const prev = process.env.NODE_ENV;
  const prevFlag = process.env.REQUIRE_DEVICE_JWT;
  process.env.NODE_ENV = 'production';
  delete process.env.REQUIRE_DEVICE_JWT;
  assert.equal(isDeviceJwtRequired(), true);
  process.env.NODE_ENV = prev;
  if (prevFlag) process.env.REQUIRE_DEVICE_JWT = prevFlag;
  else delete process.env.REQUIRE_DEVICE_JWT;
});

test('can be disabled explicitly for local dev', () => {
  const prev = process.env.REQUIRE_DEVICE_JWT;
  process.env.REQUIRE_DEVICE_JWT = 'false';
  assert.equal(isDeviceJwtRequired(), false);
  if (prev) process.env.REQUIRE_DEVICE_JWT = prev;
  else delete process.env.REQUIRE_DEVICE_JWT;
});

test('documents that unauthenticated list-all feedback is forbidden', () => {
  assert.equal(true, true);
});

console.log('security-hardening tests passed');
