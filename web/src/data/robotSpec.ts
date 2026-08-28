/**
 * Every value here is transcribed from this repository's own validated
 * documentation — README.md and docs/HANDOFF.md — not invented for the site.
 * Where a number has no repo source it is marked `status: 'planned'` or
 * `status: 'simulated'` instead of being presented as measured.
 */

export type SourceStatus = 'real' | 'simulated' | 'planned'

export interface SpecValue {
  label: string
  value: string
  status: SourceStatus
  source: string
}

export const REPO_URL = 'https://github.com/dhwanshah-cell/robospider'

export const ROBOT = {
  name: 'RoboSpider',
  platformCodename: 'CubeBot',
  dof: 12,
  legs: 4,
  jointsPerLeg: ['yaw', 'pitch', 'knee'] as const,
  massGramsMeasured: 735, // "~735 g — MEASURED, no longer an estimate" (HANDOFF.md)
  massGramsSimModel: 751.7, // sim runs at/slightly above real mass -> conservative loads
  standHeightMm: 100,
  gait: {
    crawlDutyFactor: 0.75,
    validatedFrequenciesHz: [0.8, 1.0],
    demoFrequencyHz: 1.0,
    demoStepMm: 55,
    demoStanceRaiseMm: 10,
    demoSpeedCmS: 4.0, // "1.0 Hz, 55 mm step, +10 mm stance height -> ~4 cm/s"
  },
  timestepMs: 2,
  integrator: 'implicitfast (MJX-compatible)',
  legGeometry: {
    femurMm: 48.0,
    tibiaMm: 78.82,
    reachMm: 126.82,
    footBallRadiusMm: 8.5,
  },
  legSplayDeg: { FL: 23.83, FR: -23.83, BL: 106.23, BR: -106.23 },
  jointLimitsDeg: { yaw: 91.7, pitch: 80.2, knee: 126.1 },
  footprintMm: { x: 199, y: 198 },
  wallClimbValidatedMm: 144,
  servos: [
    {
      joint: 'yaw',
      model: 'TowerPro SG90',
      stallKgCm: 1.8,
      stallNm: 0.1765,
      speed: '0.10 s/60°',
      voltage: '4.8 V',
    },
    {
      joint: 'pitch, knee',
      model: 'TowerPro SG92R',
      stallKgCm: 2.5,
      stallNm: 0.2452,
      speed: '0.10 s/60°',
      voltage: '4.8 V',
    },
  ],
  loadValidation: [
    { joint: 'yaw', worstPct: '74–84%', rmsPct: '14%', saturated: 0 },
    { joint: 'pitch', worstPct: '80–87%', rmsPct: '31%', saturated: 0 },
    { joint: 'knee', worstPct: '64–74%', rmsPct: '12%', saturated: 0 },
  ],
  validatedCases: [
    'Standing',
    'Squatting',
    '±16° body pitch',
    '±14° body roll',
    'All four tripod stances',
    'Walking at 0.8 Hz and 1.0 Hz',
    '144 mm wall-climb pose',
  ],
  sensors: [
    { name: 'Trunk framequat', purpose: 'body orientation' },
    { name: 'Trunk gyro', purpose: 'angular rate (IMU)' },
    { name: 'Trunk accelerometer', purpose: 'linear acceleration (IMU)' },
    { name: 'Trunk velocimeter', purpose: 'body velocity' },
    { name: '4× foot touch sensor', purpose: 'ground contact per leg' },
  ],
  fasteners: { m2: 58, m3: 15 },
  demoDate: '22 Aug 2026',
} as const

export const REAL_SIM_PLANNED: { status: SourceStatus; items: string[] }[] = [
  {
    status: 'real',
    items: [
      '12-DOF CubeBot chassis (4 legs × yaw/pitch/knee) — printed and assembled',
      'Robot mass — measured, ~735 g',
      'MuJoCo model validated at 751.7 g (conservative vs. measured mass)',
      'SG90 / SG92R servo set — validated standing, squat, pitch/roll, gait, and 144 mm wall-climb pose loads',
      'Onboard compute — Raspberry Pi rail (per HANDOFF.md power-staging notes)',
      'Camera Cover CAD part (mounting for an onboard camera)',
      'Crawl gait — 1.0 Hz, ~4 cm/s, physics + contact validated in MuJoCo (not kinematic playback)',
    ],
  },
  {
    status: 'simulated',
    items: [
      'Collapsed-structure environment, rubble, voids and blocked passages',
      'Communication link quality, degradation and loss',
      'Relay / mesh field extension (conceptual, not deployed)',
      'Structural hazard & accessibility classification',
      'Return-energy / battery reserve model',
      'Camera feed shown in the dashboard (Simulation Camera mode)',
      'SLAM-style spatial map and inspection coverage',
    ],
  },
  {
    status: 'planned',
    items: [
      'Production mesh radios / relay hardware',
      'Breadcrumb / relay-drop hardware',
      'Advanced structural condition estimation from sensor data',
      'Field deployment on a real collapsed-structure test site',
      'Onboard IMU part selection and integration (WT901-class or equivalent)',
    ],
  },
]

export const DEMO_FLOW = [
  'COLLAPSED STRUCTURE',
  'DEPLOY ROBOSPIDER',
  'CAMERA + IMU',
  'VISUAL / INERTIAL LOCALISATION',
  'SPATIAL MAP',
  'STRUCTURAL OBSERVATIONS',
  'COMMUNICATION STATUS',
  'HAZARD / ACCESS ASSESSMENT',
  'RETURN / MISSION COMPLETION',
] as const
