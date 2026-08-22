import { useState } from 'react'
import { Menu, X } from 'lucide-react'
import { useMissionStore } from '../../state/missionStore'
import { MissionStateBadge } from '../ui/StateBadges'

const LINKS = [
  { id: 'mission', label: '01 Mission' },
  { id: 'collapse', label: '02 Collapse' },
  { id: 'robot', label: '03 Robot' },
  { id: 'inspection', label: '04 Inspection' },
  { id: 'communication', label: '05 Comms' },
  { id: 'return', label: '06 Return' },
  { id: 'assessment', label: '07 Assessment' },
  { id: 'simulation', label: '08 Simulation' },
  { id: 'validation', label: '09 Validation' },
]

export function NavBar() {
  const [open, setOpen] = useState(false)
  const missionState = useMissionStore((s) => s.sim.missionState)

  return (
    <header className="sticky top-0 z-40 border-b border-base-700/60 bg-base-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <a href="#top" className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span className="font-mono text-sm font-bold tracking-widest text-zinc-100">ROBOSPIDER</span>
        </a>

        <nav className="hidden items-center gap-4 lg:flex">
          {LINKS.map((l) => (
            <a
              key={l.id}
              href={`#${l.id}`}
              className="font-mono text-[11px] uppercase tracking-wide text-zinc-500 transition-colors hover:text-amber-400"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <MissionStateBadge state={missionState} />
          </div>
          <button className="lg:hidden" onClick={() => setOpen((o) => !o)} aria-label="Toggle navigation">
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {open ? (
        <nav className="flex flex-col gap-1 border-t border-base-700/60 px-4 py-3 lg:hidden">
          {LINKS.map((l) => (
            <a
              key={l.id}
              href={`#${l.id}`}
              onClick={() => setOpen(false)}
              className="rounded px-2 py-1.5 font-mono text-xs uppercase tracking-wide text-zinc-400 hover:bg-base-800"
            >
              {l.label}
            </a>
          ))}
        </nav>
      ) : null}
    </header>
  )
}
