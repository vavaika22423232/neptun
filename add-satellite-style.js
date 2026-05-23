const fs = require('fs');

function addSatellite(filename, isDark) {
  const style = JSON.parse(fs.readFileSync(filename, 'utf8'));

  // Add source
  if (!style.sources.esri_satellite) {
    style.sources.esri_satellite = {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 19
    };
  }

  // Add layer right after background
  const bgIndex = style.layers.findIndex(l => l.type === 'background');
  
  // Remove existing satellite layer if any
  style.layers = style.layers.filter(l => l.id !== 'satellite_imagery');

  const satLayer = {
    id: 'satellite_imagery',
    type: 'raster',
    source: 'esri_satellite',
    paint: {
      'raster-opacity': isDark ? 0.35 : 0.25,
      'raster-saturation': isDark ? -0.8 : -0.5,
      'raster-contrast': isDark ? 0.2 : 0.1
    }
  };

  style.layers.splice(bgIndex + 1, 0, satLayer);

  // Make landuse and wood slightly transparent so satellite shows through
  style.layers.forEach(l => {
    const lid = l.id.toLowerCase();
    if (l.type === 'fill' && (lid.includes('landuse') || lid.includes('wood') || lid.includes('park') || lid.includes('glacier') || lid.includes('ice') || lid.includes('sand') || lid.includes('farmland'))) {
      if (l.paint && l.paint['fill-color']) {
        // preserve existing opacity if it's an expression, otherwise set it
        if (!Array.isArray(l.paint['fill-opacity'])) {
          l.paint['fill-opacity'] = isDark ? 0.4 : 0.5;
        }
      }
    }
  });

  fs.writeFileSync(filename, JSON.stringify(style, null, 2));
  console.log(`Updated ${filename}`);
}

addSatellite('nextjs-app/public/map-style-dark.json', true);
addSatellite('nextjs-app/public/map-style-light.json', false);
