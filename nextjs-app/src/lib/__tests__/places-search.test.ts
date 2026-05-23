import assert from 'node:assert/strict';
import test from 'node:test';
import {
  compactPlaceQuery,
  expandPlaceQueryAliases,
  normalizePlaceQuery,
} from '@/lib/places-search/normalize-query';
import { searchPlaces, isSettlementsDbAvailable } from '@/lib/places-search/db';
import { findOblastAtPoint } from '@/lib/places-search/ukraine-oblast-point';

test('normalizePlaceQuery strips prefixes and lowercases', () => {
  assert.equal(normalizePlaceQuery('  м. Київ '), 'київ');
  assert.equal(normalizePlaceQuery('с. Слобожанське'), 'слобожанське');
});

test('expandPlaceQueryAliases maps latin city names', () => {
  const variants = expandPlaceQueryAliases('kyiv');
  assert.ok(variants.includes('kyiv'));
  assert.ok(variants.includes('київ'));
});

test('compactPlaceQuery strips apostrophes for fuzzy match', () => {
  assert.equal(compactPlaceQuery("Кам'янське"), 'камянське');
  assert.equal(compactPlaceQuery('камянське'), 'камянське');
});

test('searchPlaces resolves RU spellings and apostrophe-less names', () => {
  for (const q of ['камянське', 'горловка', 'макеевка', 'алчевск', 'черноморск']) {
    const results = searchPlaces(q, 5);
    assert.ok(results.length >= 1, `expected hits for ${q}`);
  }
});

test('searchPlaces finds Kyiv from gazetteer or geojson', () => {
  const results = searchPlaces('київ', 5);
  assert.ok(results.length >= 1, 'expected at least one result');
  const kyiv = results.find((r) => r.name.toLowerCase() === 'київ');
  assert.ok(kyiv, `expected Київ in ${results.map((r) => r.name).join(', ')}`);
  assert.ok(kyiv!.subtitle.includes('обл'), `expected oblast in subtitle: ${kyiv!.subtitle}`);
});

test('searchPlaces returns multiple homonyms for common names when indexed', () => {
  if (!isSettlementsDbAvailable()) return;
  const results = searchPlaces('костянтинівка', 10);
  if (results.length > 1) {
    const subtitles = new Set(results.map((r) => r.subtitle));
    assert.ok(subtitles.size > 1, 'homonyms should differ by subtitle');
  }
});
