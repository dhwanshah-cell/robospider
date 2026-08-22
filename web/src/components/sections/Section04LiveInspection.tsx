import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { useMissionStore } from '../../state/missionStore'
import { CameraFeed } from '../sim/CameraFeed'
import { SceneMap } from '../sim/SceneMap'
import { TelemetryPanel } from '../sim/TelemetryPanel'
import { MissionStateBadge, CommStateBadge } from '../ui/StateBadges'

export function Section04LiveInspection() {
  const sim = useMissionStore((s) => s.sim)

  return (
    <Section
      id="inspection"
      index="04"
      title="Live Inspection"
      kicker="Camera / map / IMU / sensor dashboard"
      intro="Camera, spatial map and telemetry driven by the one mission simulation — not separate animations. Full operator controls live in section 08."
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Camera">
          <CameraFeed sim={sim} />
        </Panel>
        <Panel
          title="Spatial map"
          right={
            <div className="flex gap-2">
              <MissionStateBadge state={sim.missionState} />
              <CommStateBadge state={sim.commState} />
            </div>
          }
        >
          <SceneMap sim={sim} height={260} />
        </Panel>
        <Panel title="Telemetry">
          <TelemetryPanel sim={sim} />
        </Panel>
      </div>
      <a href="#simulation" className="btn btn-primary mt-4 inline-flex px-4 py-2 text-xs">
        Open full simulation console →
      </a>
    </Section>
  )
}
