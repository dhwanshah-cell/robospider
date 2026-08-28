import { DEMO_FLOW, ROBOT } from '../../data/robotSpec'
import { SourceLegend } from '../ui/SourceLegend'
import { ArrowDown } from 'lucide-react'

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage:
            'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 pb-16 pt-16 sm:px-6 sm:pt-24">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <span className="kicker">SIH25212 — Structural Stability Assessment Tool</span>
          <SourceLegend compact />
        </div>

        <div className="max-w-3xl">
          <h1 className="text-4xl font-black tracking-tight text-zinc-50 sm:text-6xl">ASSESS BEFORE YOU ENTER</h1>
          <p className="mt-3 font-mono text-sm uppercase tracking-widest text-amber-500">
            {ROBOT.name} — Robotic Structural Inspection &amp; Stability Assessment
          </p>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-zinc-400">
            A compact quadruped inspection platform that enters confined areas of collapsed structures, collects
            visual and inertial data, builds a spatial representation of the inspected environment, and supports
            safer structural access decisions.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <a href="#simulation" className="btn btn-primary px-5 py-2.5 text-sm">
            Run Simulation
          </a>
          <a href="#inspection" className="btn px-5 py-2.5 text-sm">
            Live Inspection
          </a>
          <a href="#validation" className="btn px-5 py-2.5 text-sm">
            Technical Details
          </a>
        </div>

        <div className="panel mt-4 overflow-x-auto p-4">
          <div className="mb-3 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
            System flow — judge-readable in under 60 seconds
          </div>
          <div className="flex min-w-max items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-wide">
            {DEMO_FLOW.map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                <span className="whitespace-nowrap rounded-md border border-base-600 bg-base-800 px-2.5 py-1.5 text-zinc-300">
                  {step}
                </span>
                {i < DEMO_FLOW.length - 1 ? <span className="text-amber-500">→</span> : null}
              </div>
            ))}
          </div>
        </div>

        <a href="#mission" className="flex items-center gap-1.5 self-start font-mono text-[11px] text-zinc-500 hover:text-zinc-300">
          <ArrowDown size={13} /> scroll
        </a>
      </div>
    </section>
  )
}
