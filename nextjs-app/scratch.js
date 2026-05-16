const https = require('https');
const zlib = require('zlib');
https.get('https://tiles.openfreemap.org/planet/5/19/10.pbf', (res) => {
  const chunks = [];
  res.on('data', c => chunks.push(c));
  res.on('end', () => {
    const buffer = Buffer.concat(chunks);
    const text = buffer.toString('utf-8');
    // Just find words
    console.log(text.match(/[a-zA-Z_]{3,}/g).filter(x => !['type','geometry','properties','feature'].includes(x)).slice(0, 50).join(', '));
  });
});
