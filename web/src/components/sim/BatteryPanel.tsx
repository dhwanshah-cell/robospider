import type { SimState } from '../../lib/sim/types'
import { StatTile } from '../ui/StatTile'
import { fmt1 } from '../../lib/format'

export function BatteryPanel({ sim }: { sim: SimState }) {
  const margin = sim.batteryPct - sim.returnEnergyEstimatePct - sim.safetyReservePct
  const status = sim.lowBattery
    ? 'RETURN REQUIRED'
    : sim.batteryWarning || margin <= 0
      ? 'RETURN RECOMMENDED'
      : 'SAFE TO CONTINUE'
  const tone = status === 'SAFE TO CONTINUE' ? 'ok' : status === 'RETURN RECOMMENDED' ? 'caution' : 'risk'

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3">
        <StatTile label="Battery" value={fmt1(sim.batteryPct)} unit="%" tone={tone === 'ok' ? 'ok' : tone} />
        <StatTile label="Return energy est." value={fmt1(sim.returnEnergyEstimatePct)} unit="%" small tone="cyan" />
        <StatTile label="Safety reserve" value={fmt1(sim.safetyReservePct)} unit="%" small />
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-base-700">
        <div
          className={`h-full rounded-full transition-all ${
            tone === 'ok' ? 'bg-ok' : tone === 'caution' ? 'bg-caution' : 'bg-risk'
          }`}
          style={{ width: `${Math.max(0, Math.min(100, sim.batteryPct))}%` }}
        />
      </div>

      <div className="flex items-center justify-between rounded-md border border-base-600/60 bg-base-800/50 px-3 py-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Mission status</span>
        <span
          className={`label-tag ${
            tone === 'ok' ? 'label-real' : tone === 'caution' ? 'text-caution border-caution/40 bg-caution/10' : 'label-planned text-risk border-risk/40 bg-risk/10'
          }`}
        >
          {status}
        </span>
      </div>

      <p className="font-mono text-[10px] leading-relaxed text-zinc-500">
        Switches to return when predicted return energy + safety reserve ≥ remaining battery. Thresholds are
        <span className="label-sim ml-1">simulated</span> — not validated against the physical pack.
      </p>
    </div>
  )
}
