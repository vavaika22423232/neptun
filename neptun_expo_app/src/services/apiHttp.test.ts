import assert from 'node:assert/strict';
import { ApiError, fetchJson } from './apiHttp';

async function testTimeoutError() {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (() => new Promise<Response>(() => undefined)) as typeof fetch;

  try {
    await fetchJson('https://example.test/api/health', { timeoutMs: 30 });
    assert.fail('expected timeout');
  } catch (e) {
    assert.ok(e instanceof ApiError);
    assert.match((e as ApiError).message, /timed out/i);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

async function testHttpErrorParsing() {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    ({
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ error: 'bad request' }),
    }) as Response) as typeof fetch;

  try {
    await fetchJson('https://example.test/api/x');
    assert.fail('expected ApiError');
  } catch (e) {
    assert.ok(e instanceof ApiError);
    assert.equal((e as ApiError).message, 'bad request');
    assert.equal((e as ApiError).status, 400);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

async function main() {
  await testTimeoutError();
  await testHttpErrorParsing();
  console.log('apiHttp.test.ts: ok');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
