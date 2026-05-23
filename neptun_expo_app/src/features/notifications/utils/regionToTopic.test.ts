import assert from 'node:assert/strict';
import { buildFcmTopics } from './buildFcmTopics';
import { allKnownRegionTopics, regionToTopic } from './regionToTopic';

assert.equal(regionToTopic('Харківська область'), 'region_kharkivska');
assert.equal(regionToTopic('м. Київ'), 'region_kyiv_city');
assert.ok(allKnownRegionTopics().includes('all_regions'));

const topics = buildFcmTopics(['Харківська область', 'Харківський район']);
assert.ok(topics.includes('region_kharkivska'));

const all = buildFcmTopics(
  [
    'Вінницька область',
    'Волинська область',
    'Дніпропетровська область',
    'Донецька область',
    'Житомирська область',
    'Закарпатська область',
    'Запорізька область',
    'Івано-Франківська область',
    'Київська область',
    'Кіровоградська область',
    'Луганська область',
    'Львівська область',
    'Миколаївська область',
    'Одеська область',
    'Полтавська область',
    'Рівненська область',
    'Сумська область',
    'Тернопільська область',
    'Харківська область',
    'Херсонська область',
    'Хмельницька область',
    'Черкаська область',
    'Чернівецька область',
    'Чернігівська область',
    'м. Київ',
  ],
);
assert.ok(all.includes('all_regions'));

console.log('regionToTopic.test.ts: ok');
