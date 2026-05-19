import { destinationPoint, haversineKm } from './marker-movement-policy';

const toRad = Math.PI / 180;
const toDeg = 180 / Math.PI;

function bearingBetween(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const dLng = (lng2 - lng1) * toRad;
  const l1 = lat1 * toRad;
  const l2 = lat2 * toRad;
  const y = Math.sin(dLng) * Math.cos(l2);
  const x = Math.cos(l1) * Math.sin(l2) - Math.sin(l1) * Math.cos(l2) * Math.cos(dLng);
  return (Math.atan2(y, x) * toDeg + 360) % 360;
}

export type NavCorridorSegment = {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  bearing: number;
  lengthKm: number;
  name?: string;
};

export type NavCorridor = {
  id: string;
  name: string;
  points: [number, number][]; // [lat, lng] array
  segments: NavCorridorSegment[];
};

// Hardcoded prototypes for major rivers used as drone corridors
const CORRIDORS: NavCorridor[] = [
  {
    id: 'dnipro_south',
    name: 'Dnipro River (South)',
    points: [
      [46.5, 32.3], // Estuary
      [46.6, 32.6], // Kherson
      [46.8, 33.3], // Nova Kakhovka
      [47.4, 34.0], // Nikopol region
      [47.8, 35.1], // Zaporizhzhia
      [48.4, 35.0], // Dnipro
      [48.6, 34.5], // Kamianske
    ],
    segments: [],
  },
  {
    id: 'pivdennyi_buh',
    name: 'Pivdennyi Buh',
    points: [
      [46.9, 31.9], // Mykolaiv
      [47.3, 31.7], // Nova Odesa
      [47.6, 31.3], // Voznesensk
      [48.0, 31.0], // Yuzhnoukrainsk
      [48.4, 30.5], // Pervomaisk
    ],
    segments: [],
  },
];

type GraphNode = { id: string; lat: number; lng: number };
const nodes: Record<string, GraphNode> = {};
const adjacency: Record<string, Array<{ to: string; cost: number; isCorridor: boolean }>> = {};

function addNode(id: string, lat: number, lng: number) {
  nodes[id] = { id, lat, lng };
  if (!adjacency[id]) adjacency[id] = [];
}

function addEdge(from: string, to: string, cost: number, isCorridor: boolean) {
  adjacency[from].push({ to, cost, isCorridor });
  adjacency[to].push({ to: from, cost, isCorridor });
}

// Build static graph
let nodeIdCounter = 0;
for (const corridor of CORRIDORS) {
  const nodeIds: string[] = [];
  for (let i = 0; i < corridor.points.length; i++) {
    const id = `corr_${corridor.id}_${i}`;
    addNode(id, corridor.points[i][0], corridor.points[i][1]);
    nodeIds.push(id);
  }
  for (let i = 0; i < nodeIds.length - 1; i++) {
    const p1 = corridor.points[i];
    const p2 = corridor.points[i + 1];
    const dist = haversineKm(p1[0], p1[1], p2[0], p2[1]);
    // Corridor cost weight is 0.4 (prefers corridors)
    addEdge(nodeIds[i], nodeIds[i + 1], dist * 0.4, true);
    
    // Also add segments for legacy snapToCorridor
    const bearing = bearingBetween(p1[0], p1[1], p2[0], p2[1]) || 0;
    corridor.segments.push({
      startLat: p1[0],
      startLng: p1[1],
      endLat: p2[0],
      endLng: p2[1],
      bearing,
      lengthKm: dist,
      name: corridor.name,
    });
  }
}

/**
 * A* pathfinding.
 * Finds a path from start to end, returning an array of waypoints `[lat, lng]`.
 */
function findAStarPath(startLat: number, startLng: number, targetLat: number, targetLng: number): [number, number][] {
  const startId = 'start_node';
  const endId = 'end_node';
  
  // Temporary clone of adjacency to inject start/end nodes
  const localAdj: Record<string, Array<{ to: string; cost: number; isCorridor: boolean }>> = {};
  for (const k of Object.keys(adjacency)) {
    localAdj[k] = [...adjacency[k]];
  }
  localAdj[startId] = [];
  localAdj[endId] = [];

  const localNodes: Record<string, GraphNode> = { ...nodes };
  localNodes[startId] = { id: startId, lat: startLat, lng: startLng };
  localNodes[endId] = { id: endId, lat: targetLat, lng: targetLng };

  // Connect start and end to all graph nodes + to each other
  const distStartEnd = haversineKm(startLat, startLng, targetLat, targetLng);
  // Straight line has cost weight 1.0
  localAdj[startId].push({ to: endId, cost: distStartEnd * 1.0, isCorridor: false });

  for (const nId of Object.keys(nodes)) {
    const n = nodes[nId];
    const distStart = haversineKm(startLat, startLng, n.lat, n.lng);
    // Only connect if within a reasonable distance (e.g. 50 km) to save edges, or just connect all.
    // For small graph, connecting all is fine. But we add a small penalty to enter/exit corridor to avoid zig-zags.
    const enterPenalty = 1.0;
    localAdj[startId].push({ to: nId, cost: distStart * 1.0 + enterPenalty, isCorridor: false });
    localAdj[nId].push({ to: startId, cost: distStart * 1.0 + enterPenalty, isCorridor: false });

    const distEnd = haversineKm(n.lat, n.lng, targetLat, targetLng);
    localAdj[nId].push({ to: endId, cost: distEnd * 1.0 + enterPenalty, isCorridor: false });
    localAdj[endId].push({ to: nId, cost: distEnd * 1.0 + enterPenalty, isCorridor: false });
  }

  // A* implementation
  const openSet = new Set<string>([startId]);
  const cameFrom: Record<string, string> = {};
  const gScore: Record<string, number> = {};
  for (const k of Object.keys(localNodes)) gScore[k] = Infinity;
  gScore[startId] = 0;

  const fScore: Record<string, number> = {};
  for (const k of Object.keys(localNodes)) fScore[k] = Infinity;
  fScore[startId] = distStartEnd;

  while (openSet.size > 0) {
    let current = '';
    let lowestF = Infinity;
    for (const id of openSet) {
      if (fScore[id] < lowestF) {
        lowestF = fScore[id];
        current = id;
      }
    }

    if (current === endId) {
      // Reconstruct path
      const path: [number, number][] = [];
      let curr = endId;
      while (curr in cameFrom) {
        path.unshift([localNodes[curr].lat, localNodes[curr].lng]);
        curr = cameFrom[curr];
      }
      path.unshift([startLat, startLng]);
      return path;
    }

    openSet.delete(current);

    for (const neighbor of localAdj[current]) {
      const tentative_gScore = gScore[current] + neighbor.cost;
      if (tentative_gScore < gScore[neighbor.to]) {
        cameFrom[neighbor.to] = current;
        gScore[neighbor.to] = tentative_gScore;
        const nNode = localNodes[neighbor.to];
        fScore[neighbor.to] = tentative_gScore + haversineKm(nNode.lat, nNode.lng, targetLat, targetLng) * 1.0;
        openSet.add(neighbor.to);
      }
    }
  }

  // Fallback to straight line
  return [[startLat, startLng], [targetLat, targetLng]];
}

/**
 * Given a starting position, an optional target, bearing, and distance,
 * computes the next position. If target is provided, uses A* routing over NavGraph.
 * Otherwise falls back to legacy snapToCorridor logic.
 */
export function routeAlongGraph(
  lat: number,
  lng: number,
  bearingDeg: number,
  distKm: number,
  targetPoint?: [number, number]
): { lat: number; lng: number; newBearingDeg: number } | null {
  if (distKm <= 0) return null;

  if (targetPoint) {
    const path = findAStarPath(lat, lng, targetPoint[0], targetPoint[1]);
    if (path.length >= 2) {
      // Traverse the path until distKm is exhausted
      let remainingDist = distKm;
      let curP = path[0];
      for (let i = 1; i < path.length; i++) {
        const nextP = path[i];
        const segDist = haversineKm(curP[0], curP[1], nextP[0], nextP[1]);
        if (remainingDist <= segDist) {
          const segBearing = bearingBetween(curP[0], curP[1], nextP[0], nextP[1]) || bearingDeg;
          const [fLat, fLng] = destinationPoint(curP[0], curP[1], segBearing, remainingDist);
          return { lat: fLat, lng: fLng, newBearingDeg: segBearing };
        }
        remainingDist -= segDist;
        curP = nextP;
      }
      // Reached the end of the path
      return { lat: curP[0], lng: curP[1], newBearingDeg: bearingDeg };
    }
  }

  // Legacy snapping logic
  const SEARCH_RADIUS_KM = 8.0;
  const ANGLE_TOLERANCE_DEG = 15;

  let bestSegment: NavCorridorSegment | null = null;
  let minDistance = SEARCH_RADIUS_KM;
  let reversed = false;

  for (const corridor of CORRIDORS) {
    for (const seg of corridor.segments) {
      const dist1 = haversineKm(lat, lng, seg.startLat, seg.startLng);
      const dist2 = haversineKm(lat, lng, seg.endLat, seg.endLng);
      
      let diff = Math.abs(seg.bearing - bearingDeg);
      if (diff > 180) diff = 360 - diff;
      if (diff <= ANGLE_TOLERANCE_DEG && dist1 < minDistance) {
        minDistance = dist1;
        bestSegment = seg;
        reversed = false;
      }
      
      const backBearing = (seg.bearing + 180) % 360;
      let diffBack = Math.abs(backBearing - bearingDeg);
      if (diffBack > 180) diffBack = 360 - diffBack;
      if (diffBack <= ANGLE_TOLERANCE_DEG && dist2 < minDistance) {
        minDistance = dist2;
        bestSegment = seg;
        reversed = true;
      }
    }
  }

  if (!bestSegment) return null;

  const targetBearing = reversed ? (bestSegment.bearing + 180) % 360 : bestSegment.bearing;
  const [nextLat, nextLng] = destinationPoint(lat, lng, targetBearing, distKm);
  
  const magnetLat = reversed ? bestSegment.startLat : bestSegment.endLat;
  const magnetLng = reversed ? bestSegment.startLng : bestSegment.endLng;
  const blendAlpha = Math.min(1.0, distKm / Math.max(bestSegment.lengthKm, 1));
  
  return {
    lat: nextLat * 0.7 + magnetLat * 0.3 * blendAlpha + nextLat * 0.3 * (1 - blendAlpha),
    lng: nextLng * 0.7 + magnetLng * 0.3 * blendAlpha + nextLng * 0.3 * (1 - blendAlpha),
    newBearingDeg: targetBearing,
  };
}

// Keep export for backward compatibility
export const snapToCorridor = routeAlongGraph;