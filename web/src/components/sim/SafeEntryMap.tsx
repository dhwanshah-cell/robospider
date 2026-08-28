import { SceneMap } from './SceneMap'
import type { SimState } from '../../lib/sim/types'
import { ZONE_MAP } from '../../lib/sim/environment'

export function SafeEntryMap({ sim }: { sim: SimState }) {
  const counts = { green: 0, yellow: 0, red: 0, unknown: 0 }
  Object.values(ZONE_MAP).forEach((z) => {
    const visited = sim.visitedZoneIds.has(z.id) || z.isBase
    const key = visited ? z.groundTruth.risk : 'unknown'
    counts[key] += 1
  })

  return (
    <div className="flex flex-col gap-3">
      <SceneMap sim={sim} height={280} />
      <div className="grid grid-cols-4 gap-2 text-center font-mono text-[10px]">
        <div className="rounded-md border border-ok/30 bg-ok/10 py-2">
          <div className="text-ok">{counts.green}</div>
          <div className="text-zinc-500">ACCESSIBLE</div>
        </div>
        <div className="rounded-md border border-caution/30 bg-caution/10 py-2">
          <div className="text-caution">{counts.yellow}</div>
          <div className="text-zinc-500">CAUTION</div>
        </div>
        <div className="rounded-md border border-risk/30 bg-risk/10 py-2">
          <div className="text-risk">{counts.red}</div>
          <div className="text-zinc-500">RESTRICTED</div>
        </div>
        <div className="rounded-md border border-unknown/30 bg-unknown/10 py-2">
          <div className="text-zinc-400">{counts.unknown}</div>
          <div className="text-zinc-500">UNKNOWN</div>
        </div>
      </div>
      {sim.rerouteCount > 0 ? (
        <div className="flex items-center gap-2 rounded-md border border-amber-400/30 bg-amber-400/10 px-3 py-2 font-mono text-[11px] text-amber-300">
          GREEN ENTRY → YELLOW ZONE → RED BLOCKED REGION → ALTERNATE ROUTE ({sim.rerouteCount} reroute
          {sim.rerouteCount > 1 ? 's' : ''} this mission)
        </div>
      ) : null}
    </div>
  )
}
