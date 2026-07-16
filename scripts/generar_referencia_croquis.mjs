import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';

const root = process.cwd();
const source = fs.readFileSync(path.join(root, 'public', 'mapa.js'), 'utf8');
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const geo = sandbox.window.GEO;

if (!geo?.features?.length) throw new Error('No fue posible cargar la geometría municipal.');

let minLon = Infinity;
let maxLon = -Infinity;
let minLat = Infinity;
let maxLat = -Infinity;

const polygonsOf = geometry => geometry.type === 'Polygon'
  ? [geometry.coordinates]
  : geometry.coordinates;

for (const feature of geo.features) {
  for (const polygon of polygonsOf(feature.geometry)) {
    for (const ring of polygon) {
      for (const [lon, lat] of ring) {
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
      }
    }
  }
}

const width = 1200;
const padding = 70;
const cosMid = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180);
const scale = (width - padding * 2) / ((maxLon - minLon) * cosMid);
const height = Math.round((maxLat - minLat) * scale + padding * 2);
const x = lon => padding + (lon - minLon) * cosMid * scale;
const y = lat => padding + (maxLat - lat) * scale;

const pathOf = geometry => polygonsOf(geometry)
  .map(polygon => polygon
    .map(ring => `M${ring.map(([lon, lat]) => `${x(lon).toFixed(2)},${y(lat).toFixed(2)}`).join('L')}Z`)
    .join(''))
  .join('');

const municipalPaths = geo.features.map(feature => pathOf(feature.geometry));
const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#020712"/>
  <g fill="#dceaff" stroke="#dceaff" stroke-width="3" stroke-linejoin="round">
    ${municipalPaths.map(d => `<path d="${d}"/>`).join('\n    ')}
  </g>
  <g fill="none" stroke="#377dff" stroke-width="1" opacity="0.28">
    ${municipalPaths.map(d => `<path d="${d}"/>`).join('\n    ')}
  </g>
</svg>`;

const outputDir = path.join(os.tmpdir(), 'materia-gris-croquis');
fs.mkdirSync(outputDir, { recursive: true });
const output = path.join(outputDir, 'antioquia-referencia.svg');
fs.writeFileSync(output, svg);
console.log(output);
