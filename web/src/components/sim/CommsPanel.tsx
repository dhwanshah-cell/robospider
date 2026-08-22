import type { SimState } from '../../lib/sim/types'
import { CommStateBadge } from '../ui/StateBadges'
import { StatTile } from '../ui/StatTile'

function PriorityRow({
  label,
  desc,
  active,
  degradedLabel,
}: {
  label: string
  desc: string
  active: boolean
  degradedLabel: string
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-base-600/50 bg-base-800/50 px-3 py-2">
      <div>
        <div className="font-mono text-xs font-semibold text-zinc-200">{label}</div>
        <div className="text-[11px] text-zinc-500">{desc}</div>
      </div>
      <span className={active ? 'label-real' : 'label-planned'}>{active ? 'ACTIVE' : degradedLabel}</span>
    </div>
  )
}

export function CommsPanel({ sim }: { sim: SimState }) {
  const queued = sim.unsyncedFrames + sim.unsyncedImu + sim.unsyncedPose + sim.unsyncedEvents

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Primary link</span>
        <CommStateBadge state={sim.commState} />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatTile label="Link quality" value={sim.linkQualityPct} unit="%" small tone="cyan" />
        <StatTile label="Latency" value={sim.latencyMs} unit="ms" small />
        <StatTile label="Packet loss" value={sim.packetLossPct} unit="%" small />
      </div>

      <div className="flex flex-col gap-2 border-t border-base-600/60 pt-3">
        <PriorityRow
          label="PRIORITY 0 — SAFETY"
          desc="Robot state, battery, IMU, pose, link health, fault state"
          active={sim.priority0Active}
          degradedLabel="BUFFERING LOCALLY"
        />
        <PriorityRow
          label="PRIORITY 1 — NAVIGATION"
          desc="Position, trajectory, map updates, obstacle state"
          active={sim.priority1Active}
          degradedLabel="DEGRADED"
        />
        <PriorityRow
          label="PRIORITY 2 — BULK DATA"
          desc="High-res frames, logs, historical map data"
          active={sim.priority2Active}
          degradedLabel="DEGRADED"
        />
      </div>

      <div className="flex flex-col gap-2 border-t border-base-600/60 pt-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Local data log</span>
          {sim.syncing ? <span className="label-sim">SYNCING</span> : null}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <StatTile
            label="Unsynced data queue"
            value={queued}
            unit="items"
            small
            tone={queued > 0 ? 'caution' : 'ok'}
          />
          <StatTile label="Data buffered" value={sim.dataBufferedMB.toFixed(2)} unit="MB" small />
        </div>
        <p className="font-mono text-[10px] leading-relaxed text-zinc-500">
          Frames, IMU samples, pose and events queue locally on link loss and drain to the base station once the
          link restores. Temporary loss of communication does not mean loss of data.
        </p>
      </div>

      <div className="flex items-center gap-1.5 border-t border-base-600/60 pt-3 text-[11px] text-zinc-500">
        <span className="label-tag border-amber-400/40 bg-amber-400/10 text-amber-400">
          Relay / mesh — field extension
        </span>
        <span>conceptual fallback, not a deployed physical relay</span>
      </div>
    </div>
  )
}
