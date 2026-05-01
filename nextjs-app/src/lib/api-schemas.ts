import { z } from 'zod';

/**
 * Ingest body for `/api/ingest`. The `marker` object is `.passthrough()` so the Python worker
 * can send extra fields the UI and correlator rely on, including:
 * - `resolved_oblast_hasc` — GADM HASC_1 (e.g. `UA.KK`) for region↔coord validation on the server
 * - `region_key` — stable string for spatial correlator (avoid merging different oblasts)
 * - `region`, `oblast` — free-text; used with `resolved_oblast_hasc` to snap bad geocodes
 * - `candidates` — optional alternate geocode hits for debugging / future reranking
 * - `geocode_tier` — e.g. point | multi | ambiguous (public `display_class` uses this when corroboration is missing)
 * - `candidates_count` — when `candidates` is omitted or not an array, still declare how many Nominatim/geo hits existed
 * - `geocode_source` — worker label (nominatim, internal, radar, …) for audits; not required for Zod (passthrough)
 * - `source_tier` — optional trust tier for the message channel vs geocoder (passthrough)
 * Do not treat missing ingest meta as “100% sure point”; server falls back to conservative `region_signal` + `minConfidence` edge for missing `confidence`.
 * Prefer two-stage geocoding in the worker (resolve oblast first, then search within bbox).
 */
export const IngestMarkerSchema = z.object({
  marker: z.object({
    id: z.string().max(128).optional(),
    lat: z.number().min(-90).max(90),
    lng: z.number().min(-180).max(180),
    type: z.string().max(64).optional(),
    title: z.string().max(512).optional(),
    description: z.string().max(2000).optional(),
    track_id: z.string().max(128).optional(),
    speed: z.number().optional(),
    heading: z.number().optional(),
    confidence: z.number().min(0).max(1).optional(),
    manual: z.boolean().optional(),
    positions: z.array(z.unknown()).optional(),
    channel: z.string().max(128).optional(),
    msg_id: z.union([z.string(), z.number()]).optional(),
    oblast: z.string().max(128).optional(),
    city: z.string().max(256).optional(),
  }).passthrough(),
});

export const IngestPatchSchema = z.object({
  id: z.string().min(1).max(128),
  updates: z.record(z.string(), z.unknown()).refine(
    (obj) => Object.keys(obj).length > 0,
    { message: 'Updates must not be empty' },
  ),
});

export const ChatSendSchema = z.object({
  message: z.string().min(1).max(500).optional(),
  text: z.string().min(1).max(500).optional(),
  replyTo: z.string().max(128).optional(),
  isPro: z.boolean().optional(),
  hardwareId: z.string().max(128).optional(),
  hardware_id: z.string().max(128).optional(),
  deviceId: z.string().max(128).optional(),
  nickname: z.string().max(64).optional(),
}).refine(
  (data) => data.message || data.text,
  { message: 'message is required' },
);

export const ChatModeratorBanUserSchema = z.object({
  nickname: z.string().max(64).optional(),
  deviceId: z.string().min(1).max(128),
  targetDeviceId: z.string().max(128).optional(),
  reason: z.string().max(500).optional(),
}).refine(
  (data) => data.nickname || data.targetDeviceId,
  { message: 'nickname or targetDeviceId is required' },
);

export const ChatAdminBanUserSchema = z.object({
  nickname: z.string().max(64).optional(),
  deviceId: z.string().max(128).optional(),
  reason: z.string().max(500).optional(),
}).refine(
  (data) => data.nickname || data.deviceId,
  { message: 'nickname or deviceId is required' },
);

export const ChatUnbanUserSchema = z.object({
  nickname: z.string().min(1).max(64),
  deviceId: z.string().max(128).optional(),
});

export const AuthTokenSchema = z.object({
  deviceId: z.string().min(1).max(128),
  nickname: z.string().max(64).nullable().optional(),
});

export const RegisterDeviceSchema = z.object({
  token: z.string().max(512).optional().default(''),
  regions: z.array(z.string().max(128)).max(100).optional().default([]),
  oblast_ids: z.array(z.string().max(64)).max(100).optional(),
  raion_ids: z.array(z.string().max(64)).max(500).optional(),
  device_id: z.string().min(1).max(128),
  platform: z.string().max(32).optional().default('unknown'),
  enabled: z.boolean().optional().default(true),
});

export const ImageUploadMagicBytes: Record<string, number[]> = {
  'image/jpeg': [0xFF, 0xD8, 0xFF],
  'image/png': [0x89, 0x50, 0x4E, 0x47],
  'image/gif': [0x47, 0x49, 0x46],
  'image/webp': [0x52, 0x49, 0x46, 0x46], // RIFF header
};

export function validateImageMagicBytes(buffer: Buffer, claimedMime: string): boolean {
  const expected = ImageUploadMagicBytes[claimedMime];
  if (!expected) return false;
  if (buffer.length < expected.length) return false;
  return expected.every((byte, i) => buffer[i] === byte);
}
