import type { ReactNode } from 'react'

export function StatTile({
  label,
  value,
  unit,
  tone = 'default',
  small,
}: {
  label: string
  value: ReactNode
  unit?: string
  tone?: 'default' | 'ok' | 'caution' | 'risk' | 'cyan' | 'amber'
  small?: boolean
}) {
  const toneClass: Record<string, string> = {
    default: 'text-zinc-100',
    ok: 'text-ok',
    caution: 'text-caution',
    risk: 'text-risk',
    cyan: 'text-cyan-300',
    amber: 'text-amber-400',
  }
  return (
    <div className="flex flex-col gap-0.5">
      <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className={`mono-num font-semibold ${small ? 'text-base' : 'text-xl'} ${toneClass[tone]}`}>
        {value}
        {unit ? <span className="ml-1 text-xs font-normal text-zinc-500">{unit}</span> : null}
      </div>
    </div>
  )
}
