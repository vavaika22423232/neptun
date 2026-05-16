import { readFileSync } from 'fs';
import path from 'path';
import sharp from 'sharp';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type TileParams = {
  theme: string;
  z: string;
  x: string;
  y: string;
};

type GeoJsonPolygon = {
  type: 'Polygon';
  coordinates: number[][][];
};

type GeoJsonFeatureCollection = {
  features?: Array<{
    geometry?: GeoJsonPolygon | null;
  }>;
};

const TILE_SIZE = 512;
const UA_BOUNDS = { minLng: 22.0, minLat: 44.2, maxLng: 40.2, maxLat: 52.4 } as const;
const tileCache = new Map<string, Buffer>();
let ukraineRings: number[][][] | null = null;

function loadUkraineRings(): number[][][] {
  if (ukraineRings) return ukraineRings;
  const file = path.join(process.cwd(), 'public', 'geoBoundaries-UKR-ADM0_simplified.geojson');
  const parsed = JSON.parse(readFileSync(file, 'utf8')) as GeoJsonFeatureCollection;
  const geometry = parsed.features?.[0]?.geometry;
  ukraineRings = geometry?.type === 'Polygon' ? geometry.coordinates : [];
  return ukraineRings;
}

function lonToWorldX(lng: number, z: number): number {
  return ((lng + 180) / 360) * 2 ** z;
}

function latToWorldY(lat: number, z: number): number {
  const sin = Math.sin((lat * Math.PI) / 180);
  return (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * 2 ** z;
}

function tileBounds(z: number, x: number, y: number) {
  const n = 2 ** z;
  const lng1 = (x / n) * 360 - 180;
  const lng2 = ((x + 1) / n) * 360 - 180;
  const lat1 = (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n))) * 180) / Math.PI;
  const lat2 = (Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 1)) / n))) * 180) / Math.PI;
  return { minLng: lng1, maxLng: lng2, minLat: lat2, maxLat: lat1 };
}

function intersectsUkraineBounds(z: number, x: number, y: number): boolean {
  const b = tileBounds(z, x, y);
  return (
    b.maxLng >= UA_BOUNDS.minLng &&
    b.minLng <= UA_BOUNDS.maxLng &&
    b.maxLat >= UA_BOUNDS.minLat &&
    b.minLat <= UA_BOUNDS.maxLat
  );
}

function pointToTilePx(lng: number, lat: number, z: number, x: number, y: number): [number, number] {
  return [
    (lonToWorldX(lng, z) - x) * TILE_SIZE,
    (latToWorldY(lat, z) - y) * TILE_SIZE,
  ];
}

function buildMaskSvg(z: number, x: number, y: number): Buffer {
  const paths = loadUkraineRings()
    .map((ring) => {
      const d = ring
        .map(([lng, lat], index) => {
          const [px, py] = pointToTilePx(lng, lat, z, x, y);
          return `${index === 0 ? 'M' : 'L'}${px.toFixed(2)} ${py.toFixed(2)}`;
        })
        .join(' ');
      return d ? `${d} Z` : '';
    })
    .filter(Boolean)
    .join(' ');

  return Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${TILE_SIZE}" height="${TILE_SIZE}" viewBox="0 0 ${TILE_SIZE} ${TILE_SIZE}">
      <path d="${paths}" fill="white" fill-rule="evenodd"/>
    </svg>`,
  );
}

async function transparentTile(): Promise<Buffer> {
  return sharp({
    create: {
      width: TILE_SIZE,
      height: TILE_SIZE,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .webp({ quality: 80 })
    .toBuffer();
}

function upstreamUrl(theme: string, z: number, x: number, y: number): string {
  const style = theme === 'light' ? 'DSUkraineUk' : 'DSUkraineUkDark';
  return `https://st1.deepstatemap.live/styles/${style}/${z}/${x}/${y}@2x.webp`;
}

function cacheSet(key: string, value: Buffer): void {
  if (tileCache.size > 800) {
    const first = tileCache.keys().next().value;
    if (first) tileCache.delete(first);
  }
  tileCache.set(key, value);
}

function responseBody(buffer: Buffer): ArrayBuffer {
  return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<TileParams> },
) {
  const { theme, z: zRaw, x: xRaw, y: yRaw } = await params;
  const z = Number(zRaw);
  const x = Number(xRaw);
  const y = Number(yRaw);

  if (!Number.isInteger(z) || !Number.isInteger(x) || !Number.isInteger(y) || z < 0 || z > 16) {
    return new Response('Bad tile', { status: 400 });
  }

  const cleanTheme = theme === 'light' ? 'light' : 'dark';
  const cacheKey = `${cleanTheme}/${z}/${x}/${y}`;
  const cached = tileCache.get(cacheKey);
  if (cached) {
    return new Response(responseBody(cached), {
      headers: {
        'Content-Type': 'image/webp',
        'Cache-Control': 'public, max-age=86400, stale-while-revalidate=604800',
      },
    });
  }

  try {
    let output: Buffer;
    if (!intersectsUkraineBounds(z, x, y)) {
      output = await transparentTile();
    } else {
      const upstream = await fetch(upstreamUrl(cleanTheme, z, x, y), {
        headers: { Accept: 'image/webp,image/*,*/*' },
      });
      if (!upstream.ok) {
        output = await transparentTile();
      } else {
        const input = Buffer.from(await upstream.arrayBuffer());
        const mask = buildMaskSvg(z, x, y);
        output = await sharp(input)
          .resize(TILE_SIZE, TILE_SIZE, { fit: 'fill' })
          .ensureAlpha()
          .composite([{ input: mask, blend: 'dest-in' }])
          .webp({ quality: 86 })
          .toBuffer();
      }
    }
    cacheSet(cacheKey, output);
    return new Response(responseBody(output), {
      headers: {
        'Content-Type': 'image/webp',
        'Cache-Control': 'public, max-age=86400, stale-while-revalidate=604800',
      },
    });
  } catch (error) {
    console.warn('[UKRAINE_TILE]', error);
    const output = await transparentTile();
    return new Response(responseBody(output), {
      headers: {
        'Content-Type': 'image/webp',
        'Cache-Control': 'public, max-age=60',
      },
    });
  }
}
