import { ROBOT } from '../../data/robotSpec'
import { DEFAULT_TARGET_ZONE, EDGES, ZONE_MAP, ZONES, edgeKey, findRoute } from './environment'
import type { Checkpoint, CommState, MissionState, Observation, PreCheckItem, SimState, Vec2 } from './types'

const TOTAL_ROUTE_M = EDGES.reduce((s, e) => s + e.distanceM, 0)
const DRAIN_PCT_PER_M = 2.5
const IDLE_DRAIN_PCT_PER_S = 0.015
const INSPECT_DWELL_S = 1.6
const RETURN_ENERGY_MARGIN = 1.1

export function speedForFrequency(hz: number): { cmS: number; validated: boolean } {
  const cmS = ROBOT.gait.demoSpeedCmS * (hz / ROBOT.gait.demoFrequencyHz)
  const validated = Math.abs(hz - ROBOT.gait.demoFrequencyHz) < 1e-9
  return { cmS: Math.max(0, cmS), validated }
}

function lerp(a: Vec2, b: Vec2, t: number): Vec2 {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }
}

function headingOf(a: Vec2, b: Vec2): number {
  return (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI
}

function makePreCheck(): PreCheckItem[] {
  return [
    { key: 'battery', label: 'Battery', pass: true },
    { key: 'servo', label: 'Servo system', pass: true },
    { key: 'camera', label: 'Camera', pass: true },
    { key: 'imu', label: 'IMU', pass: true },
    { key: 'storage', label: 'Storage', pass: true },
    { key: 'link', label: 'Primary Link', pass: true },
    { key: 'return', label: 'Return Path', pass: true },
  ]
}

function observationFromZone(zoneId: string, atS: number): Observation {
  const z = ZONE_MAP[zoneId]
  return {
    zoneId,
    zoneLabel: z.label,
    element: z.groundTruth.element,
    condition: z.groundTruth.condition,
    clearanceM: z.groundTruth.clearanceM,
    access: z.groundTruth.access,
    hazard: z.groundTruth.hazard,
    confidencePct: z.groundTruth.confidencePct,
    assessment: z.groundTruth.assessment,
    observedAtS: atS,
  }
}

export function initialSimState(): SimState {
  const { cmS, validated } = speedForFrequency(ROBOT.gait.demoFrequencyHz)
  return {
    missionState: 'IDLE',
    missionStatePrev: null,
    simTimeS: 0,
    running: false,

    gaitFrequencyHz: ROBOT.gait.demoFrequencyHz,
    speedCmS: cmS,
    speedValidated: validated,

    routeIds: ['BASE'],
    currentEdgeIndex: 0,
    edgeProgress: 0,
    pos: { ...ZONE_MAP.BASE.pos },
    headingDeg: 0,
    distanceTravelledM: 0,
    maxSpeedCmS: 0,

    blockedEdges: new Set(),
    rerouteCount: 0,

    visitedZoneIds: new Set(['BASE']),
    observations: [],
    mapCoveragePct: 0,

    commState: 'GOOD',
    commStatePrev: 'GOOD',
    linkQualityPct: 100,
    latencyMs: 22,
    packetLossPct: 0,
    commInterruptions: 0,
    priority0Active: true,
    priority1Active: true,
    priority2Active: true,

    unsyncedFrames: 0,
    unsyncedImu: 0,
    unsyncedPose: 0,
    unsyncedEvents: 0,
    dataBufferedMB: 0,
    syncing: false,

    batteryPct: 100,
    returnEnergyEstimatePct: 0,
    safetyReservePct: 15,
    batteryWarning: false,
    lowBattery: false,

    checkpoints: [
      { index: 0, zoneId: 'BASE', pos: { ...ZONE_MAP.BASE.pos }, headingDeg: 0, timestampS: 0, commState: 'GOOD' },
    ],
    returnCheckpointCursor: 0,
    inspectDwellS: 0,

    preCheck: makePreCheck(),
    preCheckPassed: false,

    report: null,

    log: [{ t: 0, message: 'System idle. Awaiting pre-mission check.' }],
  }
}

function clone(s: SimState): SimState {
  return {
    ...s,
    pos: { ...s.pos },
    blockedEdges: new Set(s.blockedEdges),
    rerouteCount: s.rerouteCount,
    visitedZoneIds: new Set(s.visitedZoneIds),
    observations: [...s.observations],
    checkpoints: s.checkpoints.map((c) => ({ ...c, pos: { ...c.pos } })),
    routeIds: [...s.routeIds],
    preCheck: s.preCheck.map((p) => ({ ...p })),
    log: s.log,
  }
}

function pushLog(s: SimState, message: string) {
  s.log = [{ t: Math.round(s.simTimeS * 10) / 10, message }, ...s.log].slice(0, 40)
}

/** Distance-from-base drives the "natural" link degradation. Manual overrides win. */
function naturalCommState(distFromBaseM: number): CommState {
  if (distFromBaseM < 4.5) return 'GOOD'
  if (distFromBaseM < 7.5) return 'DEGRADED'
  if (distFromBaseM < 10.3) return 'CRITICAL'
  return 'LOST'
}

const SEVERITY: Record<CommState, number> = { GOOD: 0, DEGRADED: 1, CRITICAL: 2, LOST: 3 }

function distFromBase(pos: Vec2): number {
  return Math.hypot(pos.x - ZONE_MAP.BASE.pos.x, pos.y - ZONE_MAP.BASE.pos.y)
}

function updateComms(s: SimState, commOverride: CommState | null) {
  const natural = naturalCommState(distFromBase(s.pos))
  let next: CommState = natural
  if (commOverride) {
    next = SEVERITY[commOverride] > SEVERITY[natural] ? commOverride : natural
    if (commOverride === 'LOST') next = 'LOST'
  }

  s.commStatePrev = s.commState
  if (next !== s.commState && next === 'LOST') {
    s.commInterruptions += 1
  }
  s.commState = next

  const jitter = (Math.sin(s.simTimeS * 1.7) + 1) * 2.5
  switch (next) {
    case 'GOOD':
      s.linkQualityPct = Math.round(94 + jitter)
      s.latencyMs = Math.round(20 + jitter * 3)
      s.packetLossPct = Math.round((jitter / 10) * 10) / 10
      break
    case 'DEGRADED':
      s.linkQualityPct = Math.round(55 + jitter * 2)
      s.latencyMs = Math.round(90 + jitter * 8)
      s.packetLossPct = Math.round((6 + jitter) * 10) / 10
      break
    case 'CRITICAL':
      s.linkQualityPct = Math.round(18 + jitter)
      s.latencyMs = Math.round(280 + jitter * 20)
      s.packetLossPct = Math.round((28 + jitter * 2) * 10) / 10
      break
    case 'LOST':
      s.linkQualityPct = 0
      s.latencyMs = 0
      s.packetLossPct = 100
      break
  }

  s.priority0Active = next !== 'LOST'
  s.priority1Active = next === 'GOOD' || next === 'DEGRADED'
  s.priority2Active = next === 'GOOD'

  if (next === 'LOST') {
    s.unsyncedFrames += 2
    s.unsyncedImu += 6
    s.unsyncedPose += 3
    if (Math.random() < 0.1) s.unsyncedEvents += 1
    s.dataBufferedMB = Math.round((s.dataBufferedMB + 0.42) * 100) / 100
  } else if (s.syncing || s.commStatePrev === 'LOST') {
    s.syncing = s.unsyncedFrames + s.unsyncedImu + s.unsyncedPose + s.unsyncedEvents > 0
    if (s.syncing) {
      const drain = (n: number) => Math.max(0, n - Math.ceil(n * 0.4) - 1)
      s.unsyncedFrames = drain(s.unsyncedFrames)
      s.unsyncedImu = drain(s.unsyncedImu)
      s.unsyncedPose = drain(s.unsyncedPose)
      s.unsyncedEvents = Math.max(0, s.unsyncedEvents - 1)
      if (s.unsyncedFrames + s.unsyncedImu + s.unsyncedPose + s.unsyncedEvents === 0) {
        s.syncing = false
        pushLog(s, 'Queued data sync complete. Base station updated.')
      }
    }
  }
}

function updateBattery(s: SimState) {
  const remainingRouteM = remainingDistanceToBaseM(s)
  s.returnEnergyEstimatePct = Math.round(remainingRouteM * DRAIN_PCT_PER_M * RETURN_ENERGY_MARGIN * 10) / 10
  s.lowBattery = s.batteryPct < s.safetyReservePct * 0.6
  s.batteryWarning =
    s.batteryWarning || s.batteryPct - s.returnEnergyEstimatePct - s.safetyReservePct <= 0
}

function remainingDistanceToBaseM(s: SimState): number {
  if (s.missionState === 'RETURNING' || s.missionState === 'SAFE_ZONE' || s.missionState === 'MISSION_COMPLETE') {
    let d = 0
    for (let i = s.returnCheckpointCursor; i > 0; i--) {
      const a = s.checkpoints[i].pos
      const b = s.checkpoints[i - 1].pos
      d += Math.hypot(a.x - b.x, a.y - b.y)
    }
    const cur = s.checkpoints[s.returnCheckpointCursor]
    if (cur) d += Math.hypot(s.pos.x - cur.pos.x, s.pos.y - cur.pos.y)
    return d
  }
  const route = findRoute(currentZoneId(s), 'BASE', s.blockedEdges) ?? []
  let d = 0
  for (let i = 0; i < route.length - 1; i++) {
    d += Math.hypot(
      ZONE_MAP[route[i]].pos.x - ZONE_MAP[route[i + 1]].pos.x,
      ZONE_MAP[route[i]].pos.y - ZONE_MAP[route[i + 1]].pos.y,
    )
  }
  return d
}

function currentZoneId(s: SimState): string {
  return s.routeIds[Math.min(s.currentEdgeIndex, s.routeIds.length - 1)]
}

function beginReturn(s: SimState, reason: string) {
  if (s.missionState === 'RETURNING' || s.missionState === 'SAFE_ZONE' || s.missionState === 'MISSION_COMPLETE') return
  s.missionStatePrev = s.missionState
  s.missionState = 'RETURNING'
  s.returnCheckpointCursor = s.checkpoints.length - 1
  pushLog(s, `RETURN MODE — ${reason}`)
}

function startExploreLeg(s: SimState) {
  const route = findRoute('BASE', DEFAULT_TARGET_ZONE, s.blockedEdges)
  s.routeIds = route ?? ['BASE']
  s.currentEdgeIndex = 0
  s.edgeProgress = 0
}

function advanceInspection(s: SimState, dtS: number) {
  const zoneId = currentZoneId(s)
  s.inspectDwellS += dtS
  if (s.inspectDwellS >= INSPECT_DWELL_S) {
    s.inspectDwellS = 0
    s.missionState = 'EXPLORING'
    if (zoneId === DEFAULT_TARGET_ZONE) {
      beginReturn(s, 'Inspection route complete — returning to safe zone')
    }
  }
}

function advanceExploration(s: SimState, dtS: number) {
  if (s.currentEdgeIndex >= s.routeIds.length - 1) {
    // reached end of route without hitting target logic (shouldn't normally happen)
    beginReturn(s, 'End of route reached')
    return
  }
  const fromId = s.routeIds[s.currentEdgeIndex]
  const toId = s.routeIds[s.currentEdgeIndex + 1]
  const from = ZONE_MAP[fromId].pos
  const to = ZONE_MAP[toId].pos
  const segLen = Math.max(1e-6, Math.hypot(to.x - from.x, to.y - from.y))

  const speedMS = s.speedCmS / 100
  const deltaM = speedMS * dtS
  const deltaT = deltaM / segLen

  s.edgeProgress += deltaT
  s.headingDeg = headingOf(from, to)

  if (s.edgeProgress >= 1) {
    s.pos = { ...to }
    s.distanceTravelledM += (1 - (s.edgeProgress - deltaT)) * segLen
    s.currentEdgeIndex += 1
    s.edgeProgress = 0

    if (!s.visitedZoneIds.has(toId)) {
      s.visitedZoneIds.add(toId)
      s.observations.push(observationFromZone(toId, s.simTimeS))
      s.mapCoveragePct = Math.round((s.visitedZoneIds.size / ZONES.length) * 100)
      pushLog(s, `Zone reached: ${ZONE_MAP[toId].label}`)
      s.checkpoints.push({
        index: s.checkpoints.length,
        zoneId: toId,
        pos: { ...to },
        headingDeg: s.headingDeg,
        timestampS: s.simTimeS,
        commState: s.commState,
      })
      s.missionState = 'INSPECTING'
    }
  } else {
    s.pos = lerp(from, to, s.edgeProgress)
    s.distanceTravelledM += deltaM
  }
  s.maxSpeedCmS = Math.max(s.maxSpeedCmS, s.speedCmS)
}

function advanceReturn(s: SimState, dtS: number) {
  // Always walk toward the current target checkpoint over real simulated time —
  // never snap to it, even when that target is the base checkpoint (index 0).
  const targetIdx = Math.max(0, s.returnCheckpointCursor)
  const target = s.checkpoints[targetIdx].pos
  const speedMS = s.speedCmS / 100
  const remaining = Math.hypot(target.x - s.pos.x, target.y - s.pos.y)
  const deltaM = speedMS * dtS

  if (deltaM >= remaining || remaining < 1e-3) {
    s.distanceTravelledM += remaining
    s.pos = { ...target }
    if (targetIdx <= 0) {
      s.missionState = 'SAFE_ZONE'
      pushLog(s, 'Arrived at safe zone.')
      return
    }
    s.returnCheckpointCursor = targetIdx - 1
    const prevCp = s.checkpoints[s.returnCheckpointCursor]
    s.headingDeg = headingOf(target, prevCp.pos)
  } else {
    const t = deltaM / remaining
    s.pos = lerp(s.pos, target, t)
    s.distanceTravelledM += deltaM
    s.headingDeg = headingOf(s.pos, target)
  }
  s.maxSpeedCmS = Math.max(s.maxSpeedCmS, s.speedCmS)
}

function buildReport(s: SimState): SimState['report'] {
  return {
    distanceTravelledM: Math.round(s.distanceTravelledM * 100) / 100,
    missionTimeS: Math.round(s.simTimeS * 10) / 10,
    maxSpeedCmS: Math.round(s.maxSpeedCmS * 10) / 10,
    mapCoveragePct: s.mapCoveragePct,
    observedRegions: s.observations.length,
    hazardsIdentified: s.observations.filter((o) => o.assessment !== 'LOW RISK').length,
    commInterruptions: s.commInterruptions,
    dataBufferedMB: s.dataBufferedMB,
    returnCompleted: s.missionState === 'SAFE_ZONE' || s.missionState === 'MISSION_COMPLETE',
    finalBatteryPct: Math.round(s.batteryPct * 10) / 10,
  }
}

export interface TickConfig {
  commOverride: CommState | null
}

export function tick(state: SimState, dtS: number, cfg: TickConfig): SimState {
  const s = clone(state)
  if (!s.running || s.missionState === 'IDLE' || s.missionState === 'PRE_CHECK' || s.missionState === 'PAUSED') {
    updateComms(s, cfg.commOverride)
    return s
  }

  s.simTimeS += dtS
  s.batteryPct = Math.max(0, s.batteryPct - IDLE_DRAIN_PCT_PER_S * dtS)

  updateComms(s, cfg.commOverride)

  if (s.commState === 'LOST' && (s.missionState === 'EXPLORING' || s.missionState === 'INSPECTING')) {
    beginReturn(s, 'Primary link lost')
  }

  switch (s.missionState) {
    case 'DEPLOYING': {
      s.missionState = 'EXPLORING'
      startExploreLeg(s)
      pushLog(s, 'Deployed. Beginning inspection.')
      break
    }
    case 'EXPLORING': {
      advanceExploration(s, dtS)
      s.batteryPct = Math.max(0, s.batteryPct - DRAIN_PCT_PER_M * (s.speedCmS / 100) * dtS)
      updateBattery(s)
      if (s.batteryWarning && s.missionState === 'EXPLORING') {
        beginReturn(s, 'Return-energy threshold reached')
      }
      break
    }
    case 'INSPECTING': {
      advanceInspection(s, dtS)
      updateBattery(s)
      break
    }
    case 'RETURNING': {
      advanceReturn(s, dtS)
      s.batteryPct = Math.max(0, s.batteryPct - DRAIN_PCT_PER_M * (s.speedCmS / 100) * dtS)
      updateBattery(s)
      break
    }
    case 'SAFE_ZONE': {
      s.missionState = 'MISSION_COMPLETE'
      s.report = buildReport(s)
      s.running = false
      pushLog(s, 'MISSION COMPLETE — report generated.')
      break
    }
    case 'SAFE_HOLD': {
      // holding; comms watchdog above will resume RETURNING once link recovers
      break
    }
    default:
      break
  }

  return s
}

export function setGaitFrequency(state: SimState, hz: number): SimState {
  const s = clone(state)
  const clamped = Math.min(1.4, Math.max(0.2, hz))
  const { cmS, validated } = speedForFrequency(clamped)
  s.gaitFrequencyHz = Math.round(clamped * 100) / 100
  s.speedCmS = Math.round(cmS * 100) / 100
  s.speedValidated = validated
  return s
}

export function runPreCheck(state: SimState): SimState {
  const s = clone(state)
  s.missionState = 'PRE_CHECK'
  s.preCheck = makePreCheck()
  s.preCheckPassed = true
  pushLog(s, 'Pre-mission system check: PASS. Mission ready.')
  return s
}

export function startMission(state: SimState): SimState {
  const s = clone(state)
  if (!s.preCheckPassed) return s
  s.running = true
  s.missionState = 'DEPLOYING'
  pushLog(s, 'Mission start — deploying RoboSpider.')
  return s
}

export function pauseMission(state: SimState): SimState {
  const s = clone(state)
  if (s.missionState === 'MISSION_COMPLETE' || s.missionState === 'IDLE') return s
  s.running = false
  s.missionStatePrev = s.missionState
  s.missionState = 'PAUSED'
  pushLog(s, 'Mission paused.')
  return s
}

export function resumeMission(state: SimState): SimState {
  const s = clone(state)
  if (s.missionState !== 'PAUSED') return s
  s.running = true
  s.missionState = s.missionStatePrev ?? 'EXPLORING'
  pushLog(s, 'Mission resumed.')
  return s
}

export function forceReturn(state: SimState): SimState {
  const s = clone(state)
  beginReturn(s, 'Operator commanded return')
  return s
}

export function blockCurrentRoute(state: SimState): SimState {
  const s = clone(state)
  const idx = Math.min(s.currentEdgeIndex + 1, s.routeIds.length - 1)
  const a = s.routeIds[Math.max(0, idx - 1)]
  const b = s.routeIds[idx]
  if (a && b && a !== b) {
    s.blockedEdges.add(edgeKey(a, b))
    s.blockedEdges.add(edgeKey(b, a))
    const newRoute = findRoute(currentZoneId(s), DEFAULT_TARGET_ZONE, s.blockedEdges)
    if (newRoute) {
      s.routeIds = [...s.routeIds.slice(0, s.currentEdgeIndex + 1), ...newRoute.slice(1)]
      s.rerouteCount += 1
      pushLog(s, `Route blocked ahead. Rerouting via alternate passage (reroute #${s.rerouteCount}).`)
    } else {
      pushLog(s, 'Route blocked — no alternate passage available.')
    }
  }
  return s
}

export function triggerBatteryWarning(state: SimState): SimState {
  const s = clone(state)
  s.batteryPct = Math.max(0, Math.min(s.batteryPct, s.returnEnergyEstimatePct + s.safetyReservePct + 4))
  s.batteryWarning = true
  pushLog(s, 'Battery warning injected.')
  return s
}

export function triggerLowBattery(state: SimState): SimState {
  const s = clone(state)
  s.batteryPct = Math.max(2, Math.min(s.batteryPct, s.safetyReservePct * 0.5))
  s.lowBattery = true
  s.batteryWarning = true
  pushLog(s, 'LOW BATTERY injected — emergency return.')
  return s
}

export function resetMission(): SimState {
  return initialSimState()
}

export const missionStateOrder: MissionState[] = [
  'IDLE',
  'PRE_CHECK',
  'DEPLOYING',
  'EXPLORING',
  'INSPECTING',
  'LINK_DEGRADED',
  'RETURNING',
  'SAFE_ZONE',
  'LINK_LOST',
  'SAFE_HOLD',
  'MISSION_COMPLETE',
]

export function checkpointsForDisplay(s: SimState): Checkpoint[] {
  return s.checkpoints
}

export const TOTAL_ROUTE_METRES = TOTAL_ROUTE_M
