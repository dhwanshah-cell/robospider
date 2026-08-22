export type MissionState =
  | 'IDLE'
  | 'PRE_CHECK'
  | 'DEPLOYING'
  | 'EXPLORING'
  | 'INSPECTING'
  | 'LINK_DEGRADED'
  | 'RETURNING'
  | 'SAFE_ZONE'
  | 'LINK_LOST'
  | 'SAFE_HOLD'
  | 'MISSION_COMPLETE'
  | 'PAUSED'

export type CommState = 'GOOD' | 'DEGRADED' | 'CRITICAL' | 'LOST'

export type ZoneRisk = 'unknown' | 'green' | 'yellow' | 'red'

export interface Vec2 {
  x: number
  y: number
}

export interface ZoneDef {
  id: string
  label: string
  /** top-down position, metres, base station at (0,0) */
  pos: Vec2
  /** true if this zone is the safe zone / base */
  isBase?: boolean
  /** rubble geometry for the scene (polygon points relative to pos), decorative */
  rubble?: boolean
  groundTruth: {
    element: string
    condition: string
    clearanceM: number
    access: 'CLEAR' | 'RESTRICTED' | 'BLOCKED'
    hazard: string
    confidencePct: number
    assessment: 'LOW RISK' | 'MODERATE RISK' | 'HIGH RISK'
    risk: ZoneRisk
  }
}

export interface RouteEdge {
  from: string
  to: string
  distanceM: number
}

export interface Checkpoint {
  index: number
  zoneId: string
  pos: Vec2
  headingDeg: number
  timestampS: number
  commState: CommState
}

export interface Observation {
  zoneId: string
  zoneLabel: string
  element: string
  condition: string
  clearanceM: number
  access: 'CLEAR' | 'RESTRICTED' | 'BLOCKED'
  hazard: string
  confidencePct: number
  assessment: 'LOW RISK' | 'MODERATE RISK' | 'HIGH RISK'
  observedAtS: number
}

export interface PreCheckItem {
  key: string
  label: string
  pass: boolean
}

export interface MissionReport {
  distanceTravelledM: number
  missionTimeS: number
  maxSpeedCmS: number
  mapCoveragePct: number
  observedRegions: number
  hazardsIdentified: number
  commInterruptions: number
  dataBufferedMB: number
  returnCompleted: boolean
  finalBatteryPct: number
}

export interface SimState {
  missionState: MissionState
  missionStatePrev: MissionState | null
  simTimeS: number
  running: boolean

  gaitFrequencyHz: number
  speedCmS: number
  speedValidated: boolean

  routeIds: string[]
  currentEdgeIndex: number
  edgeProgress: number // 0..1 along current edge
  pos: Vec2
  headingDeg: number
  distanceTravelledM: number
  maxSpeedCmS: number

  blockedEdges: Set<string>
  rerouteCount: number

  visitedZoneIds: Set<string>
  observations: Observation[]
  mapCoveragePct: number

  commState: CommState
  commStatePrev: CommState
  linkQualityPct: number
  latencyMs: number
  packetLossPct: number
  commInterruptions: number
  priority0Active: boolean
  priority1Active: boolean
  priority2Active: boolean

  unsyncedFrames: number
  unsyncedImu: number
  unsyncedPose: number
  unsyncedEvents: number
  dataBufferedMB: number
  syncing: boolean

  batteryPct: number
  returnEnergyEstimatePct: number
  safetyReservePct: number
  batteryWarning: boolean
  lowBattery: boolean

  checkpoints: Checkpoint[]
  returnCheckpointCursor: number
  inspectDwellS: number

  preCheck: PreCheckItem[]
  preCheckPassed: boolean

  report: MissionReport | null

  log: { t: number; message: string }[]
}
