/**
 * Attach server-computed display_* fields to SSE payloads so clients match /api/data.
 * Server-only (loadSettings + oblast polygons).
 */
import { loadSettings } from '@/lib/admin/data';
import {
  computeMarkerDisplayPolicy,
  mergeMarkerDisplayPolicyConfig,
  type CorroborationContext,
} from '@/lib/marker-display-policy';
import { isLatLngInOblastHasc } from '@/lib/ukraine-oblast-validate';
import { mapStoreRecordToMarker } from '@/lib/map-store-record-to-marker';
import { evaluateMarkerPublication } from '@/lib/public-marker-policy';

export function attachDisplayPolicyToPayload(
  fullRow: Record<string, unknown>,
  payload: Record<string, unknown>,
): void {
  const settings = loadSettings();
  const displayPolicyConfig = mergeMarkerDisplayPolicyConfig({
    corroborationMinObservations: settings.corroborationMinObservations,
    corroborationWindowMinutes: settings.corroborationWindowMinutes,
    corroborationMaxRadiusKm: settings.corroborationMaxRadiusKm,
    corroborationMinDistinctSources: settings.corroborationMinDistinctSources,
    regionUncertaintyKm: settings.regionUncertaintyKm,
    corroboratedUncertaintyKm: settings.corroboratedUncertaintyKm,
  });
  const corroborationCtx: CorroborationContext = {
    pointInStatedOblast: (lat, lng, hascUpper) => isLatLngInOblastHasc(hascUpper, lat, lng),
  };
  const marker = mapStoreRecordToMarker(fullRow);
  Object.assign(payload, computeMarkerDisplayPolicy(marker, displayPolicyConfig, corroborationCtx));
  const publication = evaluateMarkerPublication(fullRow, { settings });
  Object.assign(payload, {
    publication_class: publication.classification,
    publication_score: publication.score,
    publication_reasons: publication.reasons,
    event_fingerprint: publication.fingerprint,
  });
}
