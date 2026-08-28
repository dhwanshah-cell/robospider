import type { SimState } from '../../lib/sim/types'
import { fmtClock } from '../../lib/format'

const ASSESSMENT_TONE: Record<string, string> = {
  'LOW RISK': 'text-ok border-ok/40 bg-ok/10',
  'MODERATE RISK': 'text-caution border-caution/40 bg-caution/10',
  'HIGH RISK': 'text-risk border-risk/40 bg-risk/10',
}

export function ObservationLog({ sim }: { sim: SimState }) {
  if (sim.observations.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-base-600/60 p-6 text-center font-mono text-xs text-zinc-500">
        No regions inspected yet. Start the mission to populate structural observations.
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3">
      {sim.observations
        .slice()
        .reverse()
        .map((o) => (
          <div key={o.zoneId} className="rounded-md border border-base-600/60 bg-base-800/50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-xs font-semibold uppercase tracking-wide text-zinc-300">
                {o.zoneLabel}
              </span>
              <span className={`label-tag border px-1.5 py-0.5 ${ASSESSMENT_TONE[o.assessment]}`}>
                {o.assessment}
              </span>
            </div>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 font-mono text-[11px]">
              <dt className="text-zinc-500">Observed element</dt>
              <dd className="text-right text-zinc-300">{o.element}</dd>
              <dt className="text-zinc-500">Condition</dt>
              <dd className="text-right text-zinc-300">{o.condition}</dd>
              <dt className="text-zinc-500">Clearance</dt>
              <dd className="text-right text-zinc-300">{o.clearanceM.toFixed(2)} m</dd>
              <dt className="text-zinc-500">Access</dt>
              <dd className="text-right text-zinc-300">{o.access}</dd>
              <dt className="text-zinc-500">Hazard</dt>
              <dd className="text-right text-zinc-300">{o.hazard}</dd>
              <dt className="text-zinc-500">Confidence</dt>
              <dd className="text-right text-zinc-300">{o.confidencePct}%</dd>
              <dt className="text-zinc-500">Observed at</dt>
              <dd className="text-right text-zinc-300">T+{fmtClock(o.observedAtS)}</dd>
            </dl>
          </div>
        ))}
      <p className="font-mono text-[10px] leading-relaxed text-zinc-500">
        Preliminary decision support — not certified engineering judgement. Confidence values are simulated.
      </p>
    </div>
  )
}
