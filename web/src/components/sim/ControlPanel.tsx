import { useMissionStore } from '../../state/missionStore'

export function ControlPanel() {
  const sim = useMissionStore((s) => s.sim)
  const runPreCheck = useMissionStore((s) => s.runPreCheck)
  const start = useMissionStore((s) => s.start)
  const pause = useMissionStore((s) => s.pause)
  const resume = useMissionStore((s) => s.resume)
  const reset = useMissionStore((s) => s.reset)
  const simulateDegradation = useMissionStore((s) => s.simulateDegradation)
  const forceLinkLoss = useMissionStore((s) => s.forceLinkLoss)
  const restoreLink = useMissionStore((s) => s.restoreLink)
  const triggerBatteryWarning = useMissionStore((s) => s.triggerBatteryWarning)
  const triggerLowBattery = useMissionStore((s) => s.triggerLowBattery)
  const blockCurrentRoute = useMissionStore((s) => s.blockCurrentRoute)
  const triggerReturn = useMissionStore((s) => s.triggerReturn)
  const commOverride = useMissionStore((s) => s.commOverride)

  const idle = sim.missionState === 'IDLE'
  const preChecked = sim.missionState === 'PRE_CHECK'
  const complete = sim.missionState === 'MISSION_COMPLETE'
  const paused = sim.missionState === 'PAUSED'
  const canOperate = !idle && !preChecked && !complete
  const returning = sim.missionState === 'RETURNING' || sim.missionState === 'SAFE_ZONE'

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        {!sim.preCheckPassed ? (
          <button className="btn btn-primary col-span-2" onClick={runPreCheck} disabled={!idle}>
            Run Pre-Mission Check
          </button>
        ) : (
          <button className="btn btn-primary col-span-2" onClick={start} disabled={!preChecked}>
            Start Mission
          </button>
        )}
        <button className="btn" onClick={pause} disabled={!canOperate || paused}>
          Pause
        </button>
        <button className="btn" onClick={resume} disabled={!paused}>
          Resume
        </button>
      </div>

      <div className="border-t border-base-600/60 pt-3">
        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
          Communication fault injection
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button className="btn" onClick={simulateDegradation} disabled={!canOperate}>
            Degrade Link
          </button>
          <button className="btn btn-danger" onClick={forceLinkLoss} disabled={!canOperate}>
            Force Link Loss
          </button>
          <button className="btn col-span-2" onClick={restoreLink} disabled={!commOverride}>
            Restore Link
          </button>
        </div>
      </div>

      <div className="border-t border-base-600/60 pt-3">
        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
          Battery fault injection
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button className="btn" onClick={triggerBatteryWarning} disabled={!canOperate}>
            Battery Warning
          </button>
          <button className="btn btn-danger" onClick={triggerLowBattery} disabled={!canOperate}>
            Low Battery
          </button>
        </div>
      </div>

      <div className="border-t border-base-600/60 pt-3">
        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500">Route / mission</div>
        <div className="grid grid-cols-2 gap-2">
          <button className="btn" onClick={blockCurrentRoute} disabled={!canOperate || returning}>
            Block Route
          </button>
          <button className="btn" onClick={triggerReturn} disabled={!canOperate || returning}>
            Trigger Return
          </button>
        </div>
      </div>

      <button className="btn mt-1" onClick={reset}>
        Reset Mission
      </button>
    </div>
  )
}
