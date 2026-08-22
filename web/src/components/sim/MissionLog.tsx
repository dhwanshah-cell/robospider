import type { SimState } from '../../lib/sim/types'

export function MissionLog({ sim }: { sim: SimState }) {
  return (
    <div className="flex max-h-56 flex-col gap-1 overflow-y-auto font-mono text-[11px]">
      {sim.log.map((entry, i) => (
        <div key={i} className="flex gap-2 text-zinc-500">
          <span className="shrink-0 text-zinc-600">T+{entry.t.toFixed(1)}s</span>
          <span className="text-zinc-400">{entry.message}</span>
        </div>
      ))}
    </div>
  )
}
