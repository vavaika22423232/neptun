/**
 * Creates a proper dark map style by remapping colors from the working light style.
 * The light style has 111 layers and renders correctly.
 * We recolor it for a premium dark theme.
 */

const fs = require('fs');

const light = JSON.parse(fs.readFileSync('nextjs-app/public/map-style-light.json', 'utf8'));

// Deep clone
const dark = JSON.parse(JSON.stringify(light));

// ── Color palette ────────────────────────────────────────────────────────────
const DARK = {
  background:         '#0d1117',
  water:              '#0e1e2e',
  waterway:           '#1a2d40',
  ice:                '#151c26',
  park:               '#111d15',
  wood:               '#0f1a12',
  residential:        '#111520',
  sand:               '#1a1710',
  farmland:           '#0f1510',
  landuse:            '#111520',

  road_motorway:      '#2a3a5c',
  road_major:         '#1e2d47',
  road_minor:         '#181f30',
  road_path:          '#161c2a',
  road_pier:          '#141a28',

  railway:            '#1e293b',

  building:           '#161d2b',
  building_3d:        '#1c2438',

  boundary_state:     '#2d3a50',
  boundary_country:   '#3a4d6a',

  text_default:       '#8b9fc0',
  text_major:         '#a8bdd8',
  text_water:         '#3d5a7a',
  text_motorway:      '#4a6a9a',
};

// ── Remap paint colors ────────────────────────────────────────────────────────
function remapColor(id, origColor, type) {
  if (!origColor || typeof origColor !== 'string') return origColor;

  const lid = id.toLowerCase();

  if (type === 'background') return DARK.background;
  if (lid === 'water') return DARK.water;
  if (lid.includes('water')) return DARK.water;
  if (lid.includes('waterway')) return DARK.waterway;
  if (lid.includes('glacier') || lid.includes('ice')) return DARK.ice;
  if (lid.includes('park') || lid.includes('grass') || lid.includes('meadow')) return DARK.park;
  if (lid.includes('wood') || lid.includes('forest')) return DARK.wood;
  if (lid.includes('residential')) return DARK.residential;
  if (lid.includes('sand') || lid.includes('beach')) return DARK.sand;
  if (lid.includes('farmland') || lid.includes('farm')) return DARK.farmland;
  if (lid.includes('landuse') || lid.includes('landcover')) return DARK.landuse;

  if (lid.includes('motorway')) return DARK.road_motorway;
  if (lid.includes('major') || lid.includes('trunk') || lid.includes('primary') || lid.includes('secondary')) return DARK.road_major;
  if (lid.includes('path') || lid.includes('footway') || lid.includes('cycleway')) return DARK.road_path;
  if (lid.includes('pier')) return DARK.road_pier;
  if (lid.includes('road') || lid.includes('highway') || lid.includes('street') || lid.includes('minor')) return DARK.road_minor;

  if (lid.includes('railway') || lid.includes('transit')) return DARK.railway;

  if (lid.includes('building')) return DARK.building;

  if (lid.includes('boundary_state') || lid.includes('admin_level_4') || lid.includes('admin-2')) return DARK.boundary_state;
  if (lid.includes('boundary') || lid.includes('border') || lid.includes('admin')) return DARK.boundary_country;

  // Default: slightly lighten dark colors, darken light colors
  return '#1e2535';
}

dark.layers.forEach(layer => {
  const lid = layer.id;
  const paint = layer.paint;
  if (!paint) return;

  // Background
  if (layer.type === 'background') {
    if (paint['background-color']) paint['background-color'] = DARK.background;
    return;
  }

  // Fill layers
  if (layer.type === 'fill') {
    if (paint['fill-color']) paint['fill-color'] = remapColor(lid, paint['fill-color'], 'fill');
    if (paint['fill-outline-color']) paint['fill-outline-color'] = remapColor(lid, paint['fill-outline-color'], 'fill');
  }

  // Line layers
  if (layer.type === 'line') {
    if (paint['line-color']) paint['line-color'] = remapColor(lid, paint['line-color'], 'line');
    if (paint['line-gap-color']) paint['line-gap-color'] = remapColor(lid, paint['line-gap-color'], 'line');
  }

  // Symbol (text/icon) layers
  if (layer.type === 'symbol') {
    if (paint['text-color']) {
      const c = paint['text-color'];
      if (lid.includes('water')) {
        paint['text-color'] = DARK.text_water;
      } else if (lid.includes('motorway')) {
        paint['text-color'] = DARK.text_motorway;
      } else if (lid.includes('major') || lid.includes('city') || lid.includes('country') || lid.includes('capital')) {
        paint['text-color'] = DARK.text_major;
      } else {
        paint['text-color'] = DARK.text_default;
      }
      if (paint['text-halo-color']) paint['text-halo-color'] = '#0d1117';
    }
  }

  // Fill-extrusion (3D buildings)
  if (layer.type === 'fill-extrusion') {
    paint['fill-extrusion-color'] = DARK.building_3d;
    if (paint['fill-extrusion-opacity'] !== undefined) paint['fill-extrusion-opacity'] = 0.85;
  }
});

// Fix light settings for 3D
dark.light = {
  anchor: 'viewport',
  color: '#b8c8e8',
  intensity: 0.25,
  position: [1.15, 210, 30],
};

fs.writeFileSync('nextjs-app/public/map-style-dark.json', JSON.stringify(dark, null, 2));
console.log('Dark style written:', dark.layers.length, 'layers');
