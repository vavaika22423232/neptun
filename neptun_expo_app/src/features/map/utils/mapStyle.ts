export const tacticalDarkMapStyle = {
  version: 8,
  name: 'Neptun Tactical Dark',
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: 'OpenStreetMap',
    },
  },
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: { 'background-color': '#070A12' },
    },
    {
      id: 'osm',
      type: 'raster',
      source: 'osm',
      paint: {
        'raster-opacity': 0.28,
        'raster-saturation': -0.8,
        'raster-contrast': 0.22,
        'raster-brightness-min': 0.02,
        'raster-brightness-max': 0.48,
      },
    },
  ],
} as const;

export const tacticalLightMapStyle = {
  version: 8,
  name: 'Neptun Tactical Light',
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: 'OpenStreetMap',
    },
  },
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: { 'background-color': '#E8EEF4' },
    },
    {
      id: 'osm',
      type: 'raster',
      source: 'osm',
      paint: {
        'raster-opacity': 0.92,
        'raster-saturation': -0.15,
        'raster-contrast': 0.05,
        'raster-brightness-min': 0.05,
        'raster-brightness-max': 0.95,
      },
    },
  ],
} as const;
