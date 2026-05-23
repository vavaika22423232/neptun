import { formatTtsMessage } from './formatTtsMessage';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const msg = formatTtsMessage({
  region: 'Харківська область',
  location: 'Харків (Харківська обл.)',
  threatType: 'drone',
  alarmState: '',
  body: 'БПЛА над містом',
});

assert(msg.includes('Увага!'), 'alert prefix');
assert(msg.includes('БПЛА') || msg.includes('ударних'), 'drone threat');

const clear = formatTtsMessage({
  region: 'Київська область',
  location: '',
  threatType: '',
  alarmState: 'ended',
  body: 'відбій тривоги',
});

assert(clear.startsWith('Відбій'), 'all clear');

console.log('formatTtsMessage.test.ts: ok');
