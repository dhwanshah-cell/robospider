import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { CollapseVisual } from './CollapseVisual'

export function Section02Collapse() {
  return (
    <Section
      id="collapse"
      index="02"
      title="Collapse Scenario"
      kicker="Progressive collapse simulation"
      intro="A structure fails, becomes rubble — and that rubble is why the robot goes in, why information matters, and what decision that information supports."
    >
      <div className="grid gap-6 lg:grid-cols-5">
        <Panel title="Structural state" className="lg:col-span-3">
          <CollapseVisual />
        </Panel>
        <Panel title="Why → What → Decision" className="lg:col-span-2">
          <div className="flex flex-col gap-3 font-mono text-xs">
            <div className="rounded-md border border-base-600/60 bg-base-800/50 p-3">
              <div className="text-amber-500">WHY THE ROBOT IS DEPLOYED</div>
              <div className="mt-1 text-zinc-400">
                Confined, unstable spaces are unsafe for personnel to enter first.
              </div>
            </div>
            <div className="rounded-md border border-base-600/60 bg-base-800/50 p-3">
              <div className="text-cyan-400">WHAT INFORMATION IS OBTAINED</div>
              <div className="mt-1 text-zinc-400">
                Camera + IMU data, a spatial map, and per-zone structural observations.
              </div>
            </div>
            <div className="rounded-md border border-base-600/60 bg-base-800/50 p-3">
              <div className="text-ok">WHAT DECISION IT SUPPORTS</div>
              <div className="mt-1 text-zinc-400">
                A safe-entry map — where personnel can follow, and where they should not.
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </Section>
  )
}
