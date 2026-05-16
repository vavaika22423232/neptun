import type { StyleSpecification } from 'maplibre-gl';
import {
  resolveUaRasterTilesDarkTemplate,
  resolveUaRasterTilesLightTemplate,
} from '@/lib/map/ua-raster-fallback';

export function buildUaRasterBasemapStyle(useLightTheme: boolean): StyleSpecification {
  const tiles = [useLightTheme ? resolveUaRasterTilesLightTemplate() : resolveUaRasterTilesDarkTemplate()];
  return buildGenericRasterBasemapStyle(tiles, 'neptun-ua-raster-basemap', 4, 14);
}

export function buildGenericRasterBasemapStyle(tiles: string[], name: string, minzoom = 0, maxzoom = 22): StyleSpecification {
  return {
    version: 8,
    name,
    sources: {
      raster_basemap: {
        type: 'raster',
        tiles,
        tileSize: 256,
        minzoom,
        maxzoom,
        attribution: '',
      },
    },
    layers: [
      {
        id: 'raster-basemap-layer',
        type: 'raster',
        source: 'raster_basemap',
        minzoom,
        maxzoom,
        paint: {
          'raster-opacity': 1,
          'raster-fade-duration': 0,
        },
      },
    ],
  };
}
