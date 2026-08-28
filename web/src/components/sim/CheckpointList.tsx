import type { SimState } from '../../lib/sim/types'
import { fmtClock } from '../../lib/format'
import { CommStateBadge } from '../ui/StateBadges'

export function CheckpointList({ sim }: { sim: SimState }) {
  const returning = sim.missionState === 'RETURNING' || sim.missionState === 'SAFE_ZONE'
  return (
    <div className="flex flex-col gap-2">
      {sim.checkpoints.map((cp, i) => {
        const isActive = returning && i === sim.returnCheckpointCursor
        const isCleared = returning && i > sim.returnCheckpointCursor
        return (
          <div
            key={cp.index}
            className={`flex items-center justify-between rounded-md border px-3 py-2 font-mono text-[11px] ${
              isActive
                ? 'border-amber-500/60 bg-amber-500/10'
                : isCleared
                  ? 'border-ok/30 bg-ok/5 opacity-60'
                  : 'border-base-600/50 bg-base-800/40'
            }`}
          >
            <span className="text-zinc-300">
              P{cp.index} — {cp.zoneId}
            </span>
            <span className="text-zinc-500">
              ({cp.pos.x.toFixed(1)}, {cp.pos.y.toFixed(1)})
            </span>
            <span className="text-zinc-500">T+{fmtClock(cp.timestampS)}</span>
            <CommStateBadge state={cp.commState} />
          </div>
        )
      })}
      {sim.checkpoints.length <= 1 ? (
        <div className="rounded-md border border-dashed border-base-600/60 p-4 text-center font-mono text-xs text-zinc-500">
          Checkpoints record automatically as the robot clears each zone.
        </div>
      ) : null}
    </div>
  )
}
