import { MarkerMotionEngine } from './markerMotionEngine';

if (typeof globalThis.requestAnimationFrame !== 'function') {
  globalThis.requestAnimationFrame = (cb: FrameRequestCallback) =>
    setTimeout(() => cb(performance.now()), 16) as unknown as number;
  globalThis.cancelAnimationFrame = (id: number) => clearTimeout(id as unknown as NodeJS.Timeout);
}

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const engine = new MarkerMotionEngine();
let frames = 0;

engine.subscribe(() => {
  frames += 1;
});

engine.schedule('a', { lat: 50, lng: 30 }, { lat: 50.01, lng: 30.01 }, 90, 200);

setTimeout(() => {
  assert(frames > 0, 'motion frames emitted');
  console.log('markerMotionEngine.test.ts: ok');
  process.exit(0);
}, 80);
