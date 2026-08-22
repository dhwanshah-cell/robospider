import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { useMissionStore } from '../../state/missionStore'
import { PreMissionCheck } from '../sim/PreMissionCheck'
import { SpeedControl } from '../sim/SpeedControl'
import { ControlPanel } from '../sim/ControlPanel'
import { SceneMap } from '../sim/SceneMap'
import { CameraFeed } from '../sim/CameraFeed'
import { TelemetryPanel } from '../sim/TelemetryPanel'
import { MissionLog } from '../sim/MissionLog'
import { MissionReport } from '../sim/MissionReport'
import { MissionStateBadge, CommStateBadge } from '../ui/StateBadges'

export function Section08Simulation() {
  const sim = useMissionStore((s) => s.sim)

  return (
    <Section
      id="simulation"
      index="08"
      title="Simulation"
      kicker="Interactive collapsed-building + robot simulation"
      intro="A deterministic, stateful mission simulation — every state produces data. Browser-side physics stand-in (see section 09 for the MuJoCo validation this scales from)."
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <MissionStateBadge state={sim.missionState} />
        <CommStateBadge state={sim.commState} />
        <span className="label-sim">Simulated environment</span>
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="flex flex-col gap-4 xl:col-span-3">
          <Panel title="Pre-mission check">
            <PreMissionCheck />
          </Panel>
          <Panel title="Operator controls">
            <ControlPanel />
          </Panel>
        </div>

        <div className="flex flex-col gap-4 xl:col-span-6">
          <Panel title="Collapsed structure — top-down">
            <SceneMap sim={sim} height={320} />
          </Panel>
          <div className="grid gap-4 sm:grid-cols-2">
            <Panel title="Camera">
              <CameraFeed sim={sim} />
            </Panel>
            <Panel title="Speed">
              <SpeedControl />
            </Panel>
          </div>
        </div>

        <div className="flex flex-col gap-4 xl:col-span-3">
          <Panel title="Telemetry">
            <TelemetryPanel sim={sim} />
          </Panel>
          <Panel title="Mission log">
            <MissionLog sim={sim} />
          </Panel>
        </div>
      </div>

      {sim.report ? (
        <Panel title="Mission complete report" className="mt-4">
          <MissionReport report={sim.report} />
        </Panel>
      ) : null}
    </Section>
  )
}
