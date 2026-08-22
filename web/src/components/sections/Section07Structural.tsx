import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { useMissionStore } from '../../state/missionStore'
import { ObservationLog } from '../sim/ObservationLog'
import { SafeEntryMap } from '../sim/SafeEntryMap'

export function Section07Structural() {
  const sim = useMissionStore((s) => s.sim)

  return (
    <Section
      id="assessment"
      index="07"
      title="Structural Assessment"
      kicker="Hazard and accessibility assessment"
      intro="Where the system becomes SIH25212, not just a robot demo — mapping the inspected structure into a safe-entry decision. Preliminary decision support, not certified engineering judgement."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Structural observations">
          <ObservationLog sim={sim} />
        </Panel>
        <Panel title="Safe-entry map">
          <SafeEntryMap sim={sim} />
        </Panel>
      </div>
    </Section>
  )
}
