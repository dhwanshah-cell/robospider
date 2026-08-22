import type { RouteEdge, ZoneDef } from './types'

/**
 * Collapsed-structure scenario used by the whole simulation. Coordinates are
 * metres, top-down, base station at the origin. This is a fixed, reproducible
 * scenario (SIMULATED) — not a live sensor feed.
 */
export const ZONES: ZoneDef[] = [
  {
    id: 'BASE',
    label: 'BASE / SAFE ZONE',
    pos: { x: 0, y: 0 },
    isBase: true,
    groundTruth: {
      element: 'Safe zone perimeter',
      condition: 'Stable',
      clearanceM: 2.4,
      access: 'CLEAR',
      hazard: 'None',
      confidencePct: 100,
      assessment: 'LOW RISK',
      risk: 'green',
    },
  },
  {
    id: 'Z1',
    label: 'ZONE 01 — ENTRY CORRIDOR',
    pos: { x: 2.6, y: 0.4 },
    groundTruth: {
      element: 'Load-bearing corridor wall',
      condition: 'Intact, surface cracking only',
      clearanceM: 1.1,
      access: 'CLEAR',
      hazard: 'None significant',
      confidencePct: 91,
      assessment: 'LOW RISK',
      risk: 'green',
    },
  },
  {
    id: 'Z2',
    label: 'ZONE 02 — FOYER',
    pos: { x: 4.6, y: 1.1 },
    rubble: true,
    groundTruth: {
      element: 'Partition wall + ceiling tile debris',
      condition: 'Partially collapsed',
      clearanceM: 0.62,
      access: 'RESTRICTED',
      hazard: 'Loose debris underfoot',
      confidencePct: 78,
      assessment: 'MODERATE RISK',
      risk: 'yellow',
    },
  },
  {
    id: 'Z3',
    label: 'ZONE 03 — STAIRWELL',
    pos: { x: 6.6, y: 0.1 },
    rubble: true,
    groundTruth: {
      element: 'Stairwell soffit',
      condition: 'Fractured, hanging fragments',
      clearanceM: 0.28,
      access: 'BLOCKED',
      hazard: 'OVERHEAD INSTABILITY',
      confidencePct: 85,
      assessment: 'HIGH RISK',
      risk: 'red',
    },
  },
  {
    id: 'Z3B',
    label: 'ZONE 03B — SERVICE CORRIDOR (ALT)',
    pos: { x: 6.6, y: 2.6 },
    groundTruth: {
      element: 'Service corridor wall',
      condition: 'Intact, minor debris',
      clearanceM: 0.71,
      access: 'RESTRICTED',
      hazard: 'Reduced clearance',
      confidencePct: 80,
      assessment: 'MODERATE RISK',
      risk: 'yellow',
    },
  },
  {
    id: 'Z4',
    label: 'ZONE 04 — COLLAPSED BAY',
    pos: { x: 8.8, y: 1.4 },
    rubble: true,
    groundTruth: {
      element: 'Concrete slab',
      condition: 'Displaced',
      clearanceM: 0.31,
      access: 'RESTRICTED',
      hazard: 'OVERHEAD INSTABILITY',
      confidencePct: 82,
      assessment: 'HIGH RISK',
      risk: 'red',
    },
  },
  {
    id: 'Z5',
    label: 'ZONE 05 — DEEP VOID (TURNAROUND)',
    pos: { x: 10.6, y: 0.7 },
    groundTruth: {
      element: 'Void beneath collapsed slab',
      condition: 'Unstable rubble pile',
      clearanceM: 0.44,
      access: 'RESTRICTED',
      hazard: 'Unstable rubble',
      confidencePct: 74,
      assessment: 'MODERATE RISK',
      risk: 'yellow',
    },
  },
]

export const ZONE_MAP: Record<string, ZoneDef> = Object.fromEntries(ZONES.map((z) => [z.id, z]))

function dist(a: string, b: string): number {
  const za = ZONE_MAP[a].pos
  const zb = ZONE_MAP[b].pos
  return Math.hypot(za.x - zb.x, za.y - zb.y)
}

export const EDGES: RouteEdge[] = [
  { from: 'BASE', to: 'Z1', distanceM: dist('BASE', 'Z1') },
  { from: 'Z1', to: 'Z2', distanceM: dist('Z1', 'Z2') },
  { from: 'Z2', to: 'Z3', distanceM: dist('Z2', 'Z3') },
  { from: 'Z2', to: 'Z3B', distanceM: dist('Z2', 'Z3B') },
  { from: 'Z3', to: 'Z4', distanceM: dist('Z3', 'Z4') },
  { from: 'Z3B', to: 'Z4', distanceM: dist('Z3B', 'Z4') },
  { from: 'Z4', to: 'Z5', distanceM: dist('Z4', 'Z5') },
]

const ADJ: Record<string, { to: string; distanceM: number; key: string }[]> = {}
for (const z of ZONES) ADJ[z.id] = []
for (const e of EDGES) {
  const key = `${e.from}->${e.to}`
  const keyRev = `${e.to}->${e.from}`
  ADJ[e.from].push({ to: e.to, distanceM: e.distanceM, key })
  ADJ[e.to].push({ to: e.from, distanceM: e.distanceM, key: keyRev })
}

export function edgeKey(from: string, to: string): string {
  return `${from}->${to}`
}

/** Dijkstra shortest path from `from` to `to`, honouring a blocked-edge set. */
export function findRoute(from: string, to: string, blocked: Set<string>): string[] | null {
  const dist_: Record<string, number> = { [from]: 0 }
  const prev: Record<string, string> = {}
  const visited = new Set<string>()
  const queue = new Set<string>(ZONES.map((z) => z.id))

  while (queue.size) {
    let u: string | null = null
    let best = Infinity
    for (const id of queue) {
      const d = dist_[id] ?? Infinity
      if (d < best) {
        best = d
        u = id
      }
    }
    if (u === null) break
    queue.delete(u)
    visited.add(u)
    if (u === to) break

    for (const edge of ADJ[u]) {
      if (blocked.has(edge.key)) continue
      const alt = (dist_[u] ?? Infinity) + edge.distanceM
      if (alt < (dist_[edge.to] ?? Infinity)) {
        dist_[edge.to] = alt
        prev[edge.to] = u
      }
    }
  }

  if (!(to in dist_) || dist_[to] === Infinity) return null
  const path: string[] = [to]
  let cur = to
  while (cur !== from) {
    const p = prev[cur]
    if (!p) return null
    path.unshift(p)
    cur = p
  }
  return path
}

export const DEFAULT_TARGET_ZONE = 'Z5'
export const TOTAL_ZONES_EXCLUDING_BASE = ZONES.length - 1
