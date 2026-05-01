const fs = require('fs');

const file = 'src/components/Map/MapLibreContainer.tsx';
let code = fs.readFileSync(file, 'utf8');

// 1. Add getFirstSymbolLayerId
if (!code.includes('function getFirstSymbolLayerId')) {
  code = code.replace(
    /function districtKeyInSetExpr/,
    `function getFirstSymbolLayerId(map: maplibregl.Map): string | undefined {
  const layers = map.getStyle()?.layers;
  if (!layers) return undefined;
  for (const layer of layers) {
    if (layer.type === 'symbol') {
      return layer.id;
    }
  }
  return undefined;
}

function districtKeyInSetExpr`
  );
}

// 2. Rewrite Map initialization and onThemeChange
const mapInitRegex = /const map = new maplibregl\.Map\(\{[\s\S]*?window\.addEventListener\('theme-change', onThemeChange\);/m;

const newMapInit = `    const OFM_LIGHT = 'https://tiles.openfreemap.org/styles/liberty';
    const OFM_DARK = 'https://tiles.openfreemap.org/styles/dark';

    const map = new maplibregl.Map({
      container: mapElRef.current,
      style: { version: 8, sources: {}, layers: [] },
      center: [31.5, 48.5],
      zoom: 5,
      minZoom: 5,
      maxZoom: mapMaxZoom,
      maxBounds: [
        [18, 40],
        [44, 56],
      ],
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
    });

    const _sources: any[] = [];
    const _layers: any[] = [];
    const originalAddSource = map.addSource.bind(map);
    const originalAddLayer = map.addLayer.bind(map);

    map.addSource = (id: string, source: any) => {
      if (!_sources.find((s) => s.id === id)) {
        _sources.push({ id, source });
      }
      if (!map.getSource(id)) {
        originalAddSource(id, source);
      }
      return map;
    };

    map.addLayer = (layer: any, beforeId?: string) => {
      if (!_layers.find((l) => l.layer.id === layer.id)) {
        _layers.push({ layer, beforeId });
      }
      if (!map.getLayer(layer.id)) {
        originalAddLayer(layer, beforeId);
      }
      return map;
    };

    mapRef.current = map;

    const applyVectorStyle = async (isLight: boolean) => {
      try {
        const url = isLight ? OFM_LIGHT : OFM_DARK;
        const res = await fetch(url);
        const style = await res.json();
        
        style.layers.forEach((layer: any) => {
          if (!isLight) {
            if (layer.id === 'background') layer.paint['background-color'] = '#161a23';
            if (layer.id === 'water') layer.paint['fill-color'] = '#0b0f14';
          }
          if (layer.type === 'symbol' && layer.layout && layer.layout['text-field']) {
            layer.layout['text-field'] = ['coalesce', ['get', 'name:uk'], ['get', 'name:latin'], ['get', 'name']];
          }
        });
        
        map.setStyle(style as any);
      } catch (err) {
        console.error('Failed to load vector style', err);
      }
    };

    void applyVectorStyle(isLightMapTheme());

    const onThemeChange = () => {
      void applyVectorStyle(isLightMapTheme());
    };
    window.addEventListener('theme-change', onThemeChange);`;

code = code.replace(mapInitRegex, newMapInit);

// 3. Add style.load listener before map.on('load')
const loadRegex = /map\.on\('load', \(\) => \{[\s\S]*?setRasterTheme\(map, isLightMapTheme\(\)\);/;

const styleLoadListener = `    map.on('style.load', () => {
      if (!map.getStyle()?.layers?.length) return; // Ignore empty initial style
      
      const firstSymbolId = getFirstSymbolLayerId(map);

      // Add terrain
      if (!map.getSource('terrain')) {
        originalAddSource('terrain', {
          type: 'raster-dem',
          tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
          encoding: 'terrarium',
          tileSize: 256,
        });
        map.setTerrain({ source: 'terrain', exaggeration: 1.5 });
      }

      // Add 3D buildings
      if (!map.getLayer('3d-buildings')) {
        originalAddLayer(
          {
            id: '3d-buildings',
            source: 'openmaptiles',
            'source-layer': 'building',
            type: 'fill-extrusion',
            minzoom: 14,
            paint: {
              'fill-extrusion-color': isLightMapTheme() ? '#e5e0d8' : '#21262d',
              'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 15],
              'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
              'fill-extrusion-opacity': 0.8,
            },
          },
          firstSymbolId
        );
      }

      _sources.forEach(({ id, source }) => {
        if (!map.getSource(id)) originalAddSource(id, source);
      });

      _layers.forEach(({ layer, beforeId }) => {
        if (layer.id === UKRAINE_OUTSIDE_ADMIN_FILL_LAYER) {
          layer.paint['fill-color'] = isLightMapTheme() ? '#f5f0e6' : '#0b0f14';
        }
        if (layer.id === 'ukraine-border-stroke') {
          layer.paint['line-color'] = isLightMapTheme() ? '#1a1d21' : '#ffffff';
        }
        if (layer.id === 'district-alarm-fill') {
          layer.paint['fill-opacity'] = isLightMapTheme() ? 0.5 : 0.6;
        }

        if (layer.id === 'oblast-calm-dim' || layer.id === 'oblast-alarm-fill' || layer.id === 'district-alarm-fill' || layer.id === 'oblast-border' || layer.id === 'district-border') {
          beforeId = firstSymbolId;
        }

        if (!map.getLayer(layer.id)) originalAddLayer(layer, beforeId);
      });
    });

    map.on('load', () => {
      // setRasterTheme(map, isLightMapTheme()); // Deprecated`;

code = code.replace(loadRegex, styleLoadListener);

fs.writeFileSync(file, code);
console.log('Successfully refactored MapLibreContainer.tsx');
