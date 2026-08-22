import { useMissionStore } from '../../state/missionStore'
import { fmt1 } from '../../lib/format'

const PRESETS = [0.5, 0.8, 1.0]

export function SpeedControl() {
  const sim = useMissionStore((s) => s.sim)
  const setFrequencyHz = useMissionStore((s) => s.setFrequencyHz)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Gait frequency</span>
        {sim.speedValidated ? (
          <span className="label-real">Validated</span>
        ) : (
          <span className="label-sim">Simulated / unvalidated</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        {PRESETS.map((hz) => (
          <button
            key={hz}
            onClick={() => setFrequencyHz(hz)}
            className={`btn ${Math.abs(sim.gaitFrequencyHz - hz) < 0.01 ? 'btn-primary' : ''}`}
          >
            {hz.toFixed(1)} Hz
          </button>
        ))}
      </div>

      <input
        type="range"
        min={0.2}
        max={1.4}
        step={0.01}
        value={sim.gaitFrequencyHz}
        onChange={(e) => setFrequencyHz(parseFloat(e.target.value))}
        className="accent-amber-500"
      />

      <div className="grid grid-cols-2 gap-3 border-t border-base-600/60 pt-3">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Gait frequency</div>
          <div className="mono-num text-lg font-semibold text-zinc-100">{fmt1(sim.gaitFrequencyHz)} Hz</div>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Est. linear speed</div>
          <div className={`mono-num text-lg font-semibold ${sim.speedValidated ? 'text-ok' : 'text-cyan-300'}`}>
            {fmt1(sim.speedCmS)} cm/s
          </div>
        </div>
      </div>
      <p className="font-mono text-[10px] leading-relaxed text-zinc-500">
        Derived from the validated demo gait (1.0 Hz, 55 mm step, +10 mm stance height → ~4.0 cm/s), scaled linearly
        with frequency. Only the 1.0 Hz point is a measured/validated speed.
      </p>
    </div>
  )
}
