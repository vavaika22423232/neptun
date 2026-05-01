/**
 * Neptun Iron Stability - Snapshot Worker
 *
 * This worker acts as a "single consumer" of the dynamic API.
 * It fetches the current map state from the local Node.js server every 2 seconds
 * and persists it as a static JSON file in the public directory.
 *
 * This allows Nginx to serve 10,000+ simultaneous users from the static file (on disk/RAM)
 * while Node.js only has to process ONE request every 2 seconds.
 */

import fs from 'fs';
import path from 'path';

const API_URL = 'http://127.0.0.1:3000/api/data?timeRange=60';
const SNAPSHOT_DIR = path.resolve(process.cwd(), 'public', 'api-static');
const SNAPSHOT_PATH = path.join(SNAPSHOT_DIR, 'data.json');
const INTERVAL_MS = 2000;

console.log(`[SNAPSHOT-WORKER] Starting stabilization worker...`);
console.log(`[SNAPSHOT-WORKER] Target: ${API_URL}`);
console.log(`[SNAPSHOT-WORKER] Output: ${SNAPSHOT_PATH}`);

if (!fs.existsSync(SNAPSHOT_DIR)) {
  console.log(`[SNAPSHOT-WORKER] Creating directory: ${SNAPSHOT_DIR}`);
  fs.mkdirSync(SNAPSHOT_DIR, { recursive: true });
}

async function updateSnapshot() {
  try {
    const startTime = Date.now();
    const response = await fetch(API_URL, {
      headers: { 'User-Agent': 'Neptun-Snapshot-Worker/1.0' }
    });

    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Atomic write to prevent partial reads by Nginx
    const tmpPath = `${SNAPSHOT_PATH}.tmp`;
    fs.writeFileSync(tmpPath, JSON.stringify(data));
    fs.renameSync(tmpPath, SNAPSHOT_PATH);

    const duration = Date.now() - startTime;
    // Silent success, only log errors or slow updates
    if (duration > 1000) {
      console.warn(`[SNAPSHOT-WORKER] Slow update: ${duration}ms`);
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[SNAPSHOT-WORKER] Error: ${message}`);
  }
}

// Ensure first run is immediate
updateSnapshot();

// Periodic timer
setInterval(updateSnapshot, INTERVAL_MS);
