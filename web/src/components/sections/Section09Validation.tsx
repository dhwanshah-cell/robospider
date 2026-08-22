import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { ROBOT, REAL_SIM_PLANNED, REPO_URL } from '../../data/robotSpec'
import { SourceBadge } from '../ui/SourceLegend'

export function Section09Validation() {
  return (
    <Section
      id="validation"
      index="09"
      title="Technical Validation"
      kicker="Measured / validated robot parameters"
      intro="Real vs. simulated vs. planned, stated plainly. Nothing here is presented as measured unless it was measured."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Sensors modelled in simulation">
          <div className="flex flex-col divide-y divide-base-600/40 font-mono text-xs">
            {ROBOT.sensors.map((sn) => (
              <div key={sn.name} className="flex items-center justify-between py-2">
                <dt className="text-zinc-300">{sn.name}</dt>
                <dd className="text-zinc-500">{sn.purpose}</dd>
              </div>
            ))}
          </div>
          <p className="mt-3 font-mono text-[10px] text-zinc-500">
            Sensor suite as specified in the MuJoCo model (<code>sim/cubebot.xml</code>). Physical IMU part
            selection is <span className="label-planned">planned</span>, not yet finalised.
          </p>
        </Panel>

        <Panel title="Fasteners &amp; build status">
          <div className="flex flex-col divide-y divide-base-600/40 font-mono text-xs">
            <div className="flex items-center justify-between py-2">
              <dt className="text-zinc-300">M2 fasteners required</dt>
              <dd className="text-zinc-500">{ROBOT.fasteners.m2}</dd>
            </div>
            <div className="flex items-center justify-between py-2">
              <dt className="text-zinc-300">M3 fasteners required</dt>
              <dd className="text-zinc-500">{ROBOT.fasteners.m3}</dd>
            </div>
            <div className="flex items-center justify-between py-2">
              <dt className="text-zinc-300">Build demo date</dt>
              <dd className="text-zinc-500">{ROBOT.demoDate}</dd>
            </div>
          </div>
          <p className="mt-3 font-mono text-[10px] text-zinc-500">
            No nut traps — every screw self-taps into printed plastic. See <code>docs/HANDOFF.md</code> in the
            source repository for the live fastener count.
          </p>
        </Panel>
      </div>

      <Panel title="Real vs. simulated vs. planned" className="mt-6">
        <div className="grid gap-6 sm:grid-cols-3">
          {REAL_SIM_PLANNED.map((group) => (
            <div key={group.status}>
              <div className="mb-2">
                <SourceBadge status={group.status} />
              </div>
              <ul className="flex flex-col gap-1.5 font-mono text-[11px] text-zinc-400">
                {group.items.map((item) => (
                  <li key={item} className="flex gap-1.5">
                    <span className="text-zinc-600">›</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-6 flex items-center justify-between rounded-md border border-base-600/60 bg-base-800/50 px-4 py-3 font-mono text-xs text-zinc-500">
        <span>Source of truth for all validated values:</span>
        <a href={REPO_URL} target="_blank" rel="noreferrer" className="text-cyan-400 underline">
          {REPO_URL}
        </a>
      </div>
    </Section>
  )
}
