import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { useMissionStore } from '../../state/missionStore'
import { CommsPanel } from '../sim/CommsPanel'

function FlowBox({ label, sub }: { label: string; sub?: string }) {
  return (
    <div className="rounded-md border border-base-600 bg-base-800 px-3 py-2 text-center">
      <div className="font-mono text-[11px] font-semibold uppercase tracking-wide text-zinc-200">{label}</div>
      {sub ? <div className="font-mono text-[9px] text-zinc-500">{sub}</div> : null}
    </div>
  )
}

function Down() {
  return <div className="py-1 text-center font-mono text-amber-500">↓</div>
}

export function Section05Communication() {
  const sim = useMissionStore((s) => s.sim)

  return (
    <Section
      id="communication"
      index="05"
      title="Communication"
      kicker="Primary link, degradation, relay, local storage, fallback"
      intro="The robot is useful only if information reaches the operator and the robot can return safely. Communication is a core system feature, not an afterthought."
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Field architecture">
          <div className="flex flex-col gap-1">
            <FlowBox label="BASE STATION" />
            <Down />
            <FlowBox label="PRIMARY LINK" sub="Wi-Fi / high bandwidth" />
            <Down />
            <FlowBox label="ROBOSPIDER" />
            <div className="mt-2 grid grid-cols-3 gap-1.5">
              <FlowBox label="Camera" />
              <FlowBox label="IMU" />
              <FlowBox label="Local Log" />
            </div>
          </div>
          <div className="mt-5 border-t border-base-600/60 pt-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="label-planned">Planned / field extension</span>
            </div>
            <div className="flex flex-col gap-1 opacity-80">
              <FlowBox label="BASE" />
              <Down />
              <FlowBox label="RELAY NODE" sub="conceptual mesh fallback" />
              <Down />
              <FlowBox label="ROBOSPIDER" />
            </div>
          </div>
        </Panel>

        <Panel title="Link state machine">
          <div className="flex flex-col gap-1">
            {['GOOD', 'DEGRADED', 'CRITICAL', 'RETURN'].map((s, i, arr) => (
              <div key={s}>
                <div
                  className={`rounded-md border px-3 py-2 text-center font-mono text-xs font-semibold uppercase tracking-wide ${
                    s === sim.commState || (s === 'RETURN' && sim.missionState === 'RETURNING')
                      ? 'border-amber-500 bg-amber-500/15 text-amber-300'
                      : 'border-base-600 bg-base-800 text-zinc-400'
                  }`}
                >
                  {s}
                </div>
                {i < arr.length - 1 ? <Down /> : null}
              </div>
            ))}
          </div>
          <ul className="mt-4 flex flex-col gap-1.5 font-mono text-[10px] text-zinc-500">
            <li><span className="text-ok">GOOD</span> — high-bandwidth video, map updates, telemetry</li>
            <li><span className="text-caution">DEGRADED</span> — lower video, reduced map rate, telemetry prioritized</li>
            <li><span className="text-risk">CRITICAL</span> — robot stops advancing, prepares safe retreat</li>
            <li><span className="text-risk">LOST</span> — no further exploration, local logging, return manager activates</li>
          </ul>
        </Panel>

        <Panel title="Live link status">
          <CommsPanel sim={sim} />
        </Panel>
      </div>
    </Section>
  )
}
