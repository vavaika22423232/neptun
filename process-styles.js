const fs = require('fs');

function processDark() {
  const dark = JSON.parse(fs.readFileSync('nextjs-app/public/map-style-dark.json', 'utf8'));

  // Update background
  const bgLayer = dark.layers.find(l => l.id === 'background');
  if (bgLayer) bgLayer.paint['background-color'] = '#0a0d14'; // Deep blue-black

  // Update water
  const waterLayer = dark.layers.find(l => l.id === 'water');
  if (waterLayer) waterLayer.paint['fill-color'] = '#0f141e'; // Dark water
  
  // Update roads
  dark.layers.forEach(l => {
    if (l.id.startsWith('highway_')) {
      if (l.id.includes('motorway')) {
        l.paint['line-color'] = '#1e293b';
      } else if (l.id.includes('major')) {
        l.paint['line-color'] = '#151e2b';
      } else {
        l.paint['line-color'] = '#111827';
      }
    }
  });

  // Add 3D buildings
  const buildingIdx = dark.layers.findIndex(l => l.id === 'building');
  if (buildingIdx !== -1) {
    dark.layers[buildingIdx].paint['fill-color'] = '#161d27';
    dark.layers[buildingIdx].paint['fill-outline-color'] = '#1e293b';
    dark.layers[buildingIdx].maxzoom = 14;

    dark.layers.splice(buildingIdx + 1, 0, {
      id: 'building-3d',
      type: 'fill-extrusion',
      source: 'openmaptiles',
      'source-layer': 'building',
      minzoom: 14,
      paint: {
        'fill-extrusion-base': ['get', 'render_min_height'],
        'fill-extrusion-color': '#161d27',
        'fill-extrusion-height': ['get', 'render_height'],
        'fill-extrusion-opacity': 0.8
      }
    });
  }

  // Add light
  dark.light = {
    anchor: 'viewport',
    color: '#ffffff',
    intensity: 0.15,
    position: [1.15, 210, 30]
  };

  fs.writeFileSync('nextjs-app/public/map-style-dark.json', JSON.stringify(dark, null, 2));
}

function processLight() {
  const light = JSON.parse(fs.readFileSync('nextjs-app/public/map-style-light.json', 'utf8'));

  // Update background
  const bgLayer = light.layers.find(l => l.id === 'background');
  if (bgLayer) bgLayer.paint['background-color'] = '#f4f4f5'; // Light gray

  // Update water
  const waterLayer = light.layers.find(l => l.id === 'water');
  if (waterLayer) waterLayer.paint['fill-color'] = '#a5c2f5'; // Pastel water (Apple Maps style)
  
  // Update roads
  light.layers.forEach(l => {
    if (l.id.startsWith('road_') || l.id.startsWith('tunnel_') || l.id.startsWith('bridge_')) {
      if (l.paint && l.paint['line-color']) {
        if (l.id.includes('motorway')) {
          l.paint['line-color'] = '#ffffff';
        } else {
          l.paint['line-color'] = '#ffffff';
        }
      }
    }
  });

  // Update 3D buildings
  const building3d = light.layers.find(l => l.id === 'building-3d');
  if (building3d) {
    building3d.paint['fill-extrusion-color'] = '#e4e4e7';
    building3d.paint['fill-extrusion-opacity'] = 0.9;
  }
  const building = light.layers.find(l => l.id === 'building');
  if (building) {
    building.paint['fill-color'] = '#e4e4e7';
  }

  // Add light
  light.light = {
    anchor: 'viewport',
    color: '#ffffff',
    intensity: 0.3,
    position: [1.15, 210, 30]
  };

  fs.writeFileSync('nextjs-app/public/map-style-light.json', JSON.stringify(light, null, 2));
}

processDark();
processLight();
