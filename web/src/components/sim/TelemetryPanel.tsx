import { StatTile } from '../ui/StatTile'
import { fmt1, fmt2, fmtClock } from '../../lib/format'
import type { SimState } from '../../lib/sim/types'

function pseudoAttitude(sim: SimState) {
  const w = sim.gaitFrequencyHz * 2 * Math.PI
  const moving = sim.missionState === 'EXPLORING' || sim.missionState === 'RETURNING'
  const amp = moving ? 1 : 0.15
  const roll = Math.sin(sim.simTimeS * w) * amp * 2.1
  const pitch = Math.sin(sim.simTimeS * w * 0.5 + 1) * amp * 1.4
  return { roll, pitch }
}

export function TelemetryPanel({ sim }: { sim: SimState }) {
  const { roll, pitch } = pseudoAttitude(sim)
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
      <StatTile label="Position X" value={fmt2(sim.pos.x)} unit="m" small />
      <StatTile label="Position Y" value={fmt2(sim.pos.y)} unit="m" small />
      <StatTile label="Heading" value={fmtInt0(sim.headingDeg)} unit="deg" small />
      <StatTile label="Speed" value={fmt1(sim.speedCmS)} unit="cm/s" tone="cyan" small />
      <StatTile label="Roll" value={fmt1(roll)} unit="deg" small />
      <StatTile label="Pitch" value={fmt1(pitch)} unit="deg" small />
      <StatTile
        label="Battery"
        value={fmt1(sim.batteryPct)}
        unit="%"
        tone={sim.lowBattery ? 'risk' : sim.batteryWarning ? 'caution' : 'ok'}
        small
      />
      <StatTile label="Sim time" value={fmtClock(sim.simTimeS)} small />
      <StatTile label="Distance" value={fmt2(sim.distanceTravelledM)} unit="m" small />
    </div>
  )
}

function fmtInt0(n: number): string {
  const v = ((n % 360) + 360) % 360
  return Math.round(v).toString()
}
