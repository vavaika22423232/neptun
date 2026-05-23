import { resolveThreatKey, isThreatTypeAllowed } from './resolveThreatKey';
import { shouldShowNotification } from '../services/notificationFilterService';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

assert(resolveThreatKey('ракета над містом', '') === 'rocket', 'rocket key');
assert(resolveThreatKey('', 'бпла') === 'drones', 'drone key');
assert(isThreatTypeAllowed('rocket', ['drones']) === false, 'threat filter');
assert(isThreatTypeAllowed('rocket', []) === true, 'empty allowed');

assert(
  shouldShowNotification(
    { oblastId: '19', raionId: 'UA-63-04' },
    { oblastIds: new Set(), raionIds: new Set(['UA-63-04']), settlementId: null },
  ),
  'raion match',
);

console.log('fcmMessagePipeline.test.ts: ok');
