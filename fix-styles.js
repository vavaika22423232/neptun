const fs = require('fs');

function processDark() {
  const dark = JSON.parse(fs.readFileSync('nextjs-app/public/map-style-dark.json', 'utf8'));

  const building3d = dark.layers.find(l => l.id === 'building-3d');
  if (building3d) {
    building3d.paint['fill-extrusion-height'] = ['coalesce', ['get', 'render_height'], ['get', 'height'], 15];
    building3d.paint['fill-extrusion-base'] = ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0];
  }

  fs.writeFileSync('nextjs-app/public/map-style-dark.json', JSON.stringify(dark, null, 2));
}

function processLight() {
  const light = JSON.parse(fs.readFileSync('nextjs-app/public/map-style-light.json', 'utf8'));

  // Add 3D buildings if not exists
  const buildingIdx = light.layers.findIndex(l => l.id === 'building');
  if (buildingIdx !== -1) {
    const existing3d = light.layers.find(l => l.id === 'building-3d');
    if (!existing3d) {
      light.layers.splice(buildingIdx + 1, 0, {
        id: 'building-3d',
        type: 'fill-extrusion',
        source: 'openmaptiles',
        'source-layer': 'building',
        minzoom: 14,
        paint: {
          'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
          'fill-extrusion-color': '#e4e4e7',
          'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 15],
          'fill-extrusion-opacity': 0.9
        }
      });
    } else {
      existing3d.paint['fill-extrusion-height'] = ['coalesce', ['get', 'render_height'], ['get', 'height'], 15];
      existing3d.paint['fill-extrusion-base'] = ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0];
    }
  }

  fs.writeFileSync('nextjs-app/public/map-style-light.json', JSON.stringify(light, null, 2));
}

processDark();
processLight();
