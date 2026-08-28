import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { useMissionStore } from '../../state/missionStore'
import { CheckpointList } from '../sim/CheckpointList'
import { BatteryPanel } from '../sim/BatteryPanel'

const FLOW = ['EXPLORATION', 'LINK LOSS / LOW BATTERY', 'STOP', 'RETURN MODE', 'BACKTRACK CHECKPOINTS', 'BASE']

export function Section06Return() {
  const sim = useMissionStore((s) => s.sim)

  return (
    <Section
      id="return"
      index="06"
      title="Return"
      kicker="Return-to-safe-zone logic"
      intro="The robot never teleports back. It records checkpoints while exploring and traverses them backward in real simulated time, restoring communication as connectivity allows."
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Return sequence">
          <div className="flex flex-col gap-1">
            {FLOW.map((s, i) => (
              <div key={s}>
                <div className="rounded-md border border-base-600 bg-base-800 px-3 py-2 text-center font-mono text-[11px] font-semibold uppercase tracking-wide text-zinc-300">
                  {s}
                </div>
                {i < FLOW.length - 1 ? <div className="py-1 text-center font-mono text-amber-500">↓</div> : null}
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Checkpoints"
          right={<span className="font-mono text-[10px] text-zinc-500">P0 → P{Math.max(0, sim.checkpoints.length - 1)}</span>}
        >
          <CheckpointList sim={sim} />
        </Panel>

        <Panel title="Battery-based return">
          <BatteryPanel sim={sim} />
        </Panel>
      </div>
    </Section>
  )
}
