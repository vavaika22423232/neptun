const style = require('./ofm-dark-pretty.json');
style.layers.forEach(layer => {
  // Update colors
  if (layer.id === 'background') {
    layer.paint['background-color'] = '#161a23';
  }
  if (layer.id === 'water') {
    layer.paint['fill-color'] = '#0b0f14';
  }
  if (layer.id === 'building') {
    layer.paint['fill-color'] = '#21262d';
  }
  
  // Update text language to Ukrainian
  if (layer.type === 'symbol' && layer.layout && layer.layout['text-field']) {
    layer.layout['text-field'] = ['coalesce', ['get', 'name:uk'], ['get', 'name:latin'], ['get', 'name']];
  }
});
require('fs').writeFileSync('ofm-dark-custom.json', JSON.stringify(style, null, 2));
