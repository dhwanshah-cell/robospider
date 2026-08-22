import { ZONE_MAP } from '../../lib/sim/environment'
import type { SimState } from '../../lib/sim/types'
import { fmtClock } from '../../lib/format'

const RISK_TINT: Record<string, string> = {
  unknown: '#1c2028',
  green: '#123a24',
  yellow: '#3a3312',
  red: '#3a1512',
}

export function CameraFeed({ sim }: { sim: SimState }) {
  const zoneId = sim.routeIds[Math.min(sim.currentEdgeIndex, sim.routeIds.length - 1)]
  const zone = ZONE_MAP[zoneId] ?? ZONE_MAP.BASE
  const visited = sim.visitedZoneIds.has(zone.id)
  const risk = visited || zone.isBase ? zone.groundTruth.risk : 'unknown'
  const videoLive = sim.priority2Active
  const noiseOpacity = videoLive ? 0.03 : sim.commState === 'DEGRADED' ? 0.35 : 0.75

  return (
    <div
      className="relative aspect-video w-full overflow-hidden rounded-md border border-base-600/60"
      style={{ background: `radial-gradient(circle at 30% 20%, ${RISK_TINT[risk]}, #08090b 75%)` }}
    >
      <svg className="absolute inset-0 h-full w-full opacity-40" preserveAspectRatio="none">
        <defs>
          <filter id="camNoise">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
        </defs>
        <rect width="100%" height="100%" filter="url(#camNoise)" opacity={noiseOpacity} />
      </svg>

      <svg className="absolute inset-0 h-full w-full opacity-[0.08]" preserveAspectRatio="none">
        {Array.from({ length: 24 }).map((_, i) => (
          <line key={i} x1="0" x2="100%" y1={`${i * 4.2}%`} y2={`${i * 4.2}%`} stroke="#fff" strokeWidth={1} />
        ))}
      </svg>

      <div className="absolute inset-x-0 top-0 flex items-center justify-between p-2.5 font-mono text-[10px] uppercase tracking-wider text-zinc-300">
        <span className="flex items-center gap-1.5 rounded bg-black/50 px-1.5 py-0.5">
          <span className={`h-1.5 w-1.5 rounded-full ${sim.running ? 'animate-pulse bg-risk' : 'bg-zinc-500'}`} />
          {sim.running ? 'REC' : 'STANDBY'}
        </span>
        <span className="rounded bg-black/50 px-1.5 py-0.5 text-cyan-300">SIMULATION CAMERA</span>
      </div>

      <div className="absolute inset-x-0 bottom-0 flex items-end justify-between p-2.5 font-mono text-[10px] text-zinc-300">
        <span className="rounded bg-black/50 px-1.5 py-0.5">{zone.label}</span>
        <span className="rounded bg-black/50 px-1.5 py-0.5">T+{fmtClock(sim.simTimeS)}</span>
      </div>

      {!videoLive ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="label-tag border-risk/60 bg-black/70 px-2 py-1 text-risk">VIDEO LINK DEGRADED</span>
        </div>
      ) : null}
    </div>
  )
}
