import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'

const UNKNOWNS = [
  'Which areas are accessible',
  'Which areas are structurally hazardous',
  'Where debris blocks movement',
  'Whether a passage is sufficiently clear',
  'What has already been inspected',
  'What lies beyond a dangerous entry point',
  'Whether the inspection robot can safely return',
]

export function Section01Mission() {
  return (
    <Section id="mission" index="01" title="Mission" kicker="Problem + purpose">
      <div className="grid gap-6 lg:grid-cols-5">
        <Panel title="The problem" className="lg:col-span-3">
          <p className="mb-4 text-sm leading-relaxed text-zinc-300">
            After a structural collapse, rescue personnel often do not know:
          </p>
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {UNKNOWNS.map((u) => (
              <li key={u} className="flex items-start gap-2 font-mono text-xs text-zinc-400">
                <span className="mt-0.5 text-amber-500">›</span>
                {u}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="What RoboSpider is" className="lg:col-span-2">
          <p className="text-sm leading-relaxed text-zinc-300">
            The robot is a <strong className="text-zinc-100">mobile inspection platform</strong> — it collects
            visual and inertial information inside hazardous or confined regions.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-zinc-300">
            The actual solution is the{' '}
            <strong className="text-zinc-100">
              structural inspection, mapping, hazard assessment and safe-entry decision-support system
            </strong>{' '}
            built around it — not the robot walking through rubble on its own.
          </p>
          <div className="mt-4 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 font-mono text-xs text-amber-300">
            This is not an autonomous rescue robot. It is a structural stability assessment tool.
          </div>
        </Panel>
      </div>
    </Section>
  )
}
