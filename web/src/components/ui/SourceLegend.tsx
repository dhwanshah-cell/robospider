export function SourceLegend({ compact }: { compact?: boolean }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-4 gap-y-1.5 ${compact ? 'text-[10px]' : 'text-xs'}`}>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-ok" /> Real hardware
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-cyan-400" /> Simulated
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-amber-400" /> Planned / field extension
      </span>
    </div>
  )
}

export function SourceBadge({ status }: { status: 'real' | 'simulated' | 'planned' }) {
  if (status === 'real') return <span className="label-real">🟢 Real</span>
  if (status === 'simulated') return <span className="label-sim">🔵 Simulated</span>
  return <span className="label-planned">🟡 Planned</span>
}
