import { REPO_URL, ROBOT } from '../../data/robotSpec'
import { SourceLegend } from '../ui/SourceLegend'

export function Footer() {
  return (
    <footer className="border-t border-base-700/60 py-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="font-mono text-xs text-zinc-500">
            {ROBOT.name} — Structural Stability Assessment Tool · SIH25212
          </div>
          <SourceLegend compact />
        </div>
        <div className="font-mono text-[11px] text-zinc-600">
          Engineering reference:{' '}
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="text-cyan-400 underline">
            {REPO_URL}
          </a>
        </div>
      </div>
    </footer>
  )
}
