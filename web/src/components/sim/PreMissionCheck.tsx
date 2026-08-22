import { useMissionStore } from '../../state/missionStore'

export function PreMissionCheck() {
  const sim = useMissionStore((s) => s.sim)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs font-semibold uppercase tracking-wider text-zinc-400">
          System check
        </span>
        {sim.preCheckPassed ? <span className="label-real">Mission ready</span> : null}
      </div>
      <div className="flex flex-col divide-y divide-base-600/50 rounded-md border border-base-600/50">
        {sim.preCheck.map((item) => (
          <div key={item.key} className="flex items-center justify-between px-3 py-2 font-mono text-xs">
            <span className="text-zinc-400">{item.label}</span>
            <span className={item.pass ? 'text-ok' : 'text-risk'}>{item.pass ? 'PASS' : 'FAIL'}</span>
          </div>
        ))}
        <div className="flex items-center justify-between px-3 py-2 font-mono text-xs">
          <span className="text-zinc-400">Return Path</span>
          <span className="text-ok">READY</span>
        </div>
      </div>
      {!sim.preCheckPassed ? (
        <p className="font-mono text-[10px] text-zinc-500">Run the check from the control panel to proceed.</p>
      ) : null}
    </div>
  )
}
