import { Section } from '../layout/Section'
import { Panel } from '../ui/Panel'
import { ROBOT, REPO_URL } from '../../data/robotSpec'
import { SourceBadge } from '../ui/SourceLegend'

export function Section03Robot() {
  return (
    <Section
      id="robot"
      index="03"
      title="Robot"
      kicker="RoboSpider / CubeBot physical specifications"
      intro={
        <>
          Values sourced directly from the validated engineering repository —{' '}
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="text-cyan-400 underline">
            dhwanshah-cell/robospider
          </a>
          .
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Platform" right={<SourceBadge status="real" />}>
          <dl className="flex flex-col divide-y divide-base-600/40 font-mono text-xs">
            {[
              ['Degrees of freedom', `${ROBOT.dof} (4 legs × yaw/pitch/knee)`],
              ['Mass — measured', `~${ROBOT.massGramsMeasured} g`],
              ['Mass — sim-validated at', `${ROBOT.massGramsSimModel} g`],
              ['Stand height', `${ROBOT.standHeightMm} mm on four feet`],
              ['Femur length', `${ROBOT.legGeometry.femurMm} mm`],
              ['Tibia length', `${ROBOT.legGeometry.tibiaMm} mm`],
              ['Leg reach', `${ROBOT.legGeometry.reachMm} mm`],
              ['Foot ball radius', `${ROBOT.legGeometry.footBallRadiusMm} mm`],
              ['Footprint', `${ROBOT.footprintMm.x} × ${ROBOT.footprintMm.y} mm`],
              ['Wall-climb, validated', `${ROBOT.wallClimbValidatedMm} mm`],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-2">
                <dt className="text-zinc-500">{k}</dt>
                <dd className="text-zinc-200">{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>

        <Panel title="Gait &amp; simulation" right={<SourceBadge status="real" />}>
          <dl className="flex flex-col divide-y divide-base-600/40 font-mono text-xs">
            {[
              ['Crawl duty factor', ROBOT.gait.crawlDutyFactor],
              ['Validated frequencies', `${ROBOT.gait.validatedFrequenciesHz.join(' / ')} Hz`],
              ['Demo gait', `${ROBOT.gait.demoFrequencyHz} Hz, ${ROBOT.gait.demoStepMm} mm step`],
              ['Demo speed', `~${ROBOT.gait.demoSpeedCmS} cm/s`],
              ['Timestep', `${ROBOT.timestepMs} ms`],
              ['Integrator', ROBOT.integrator],
              ['Joint limit — yaw', `±${ROBOT.jointLimitsDeg.yaw}°`],
              ['Joint limit — pitch', `±${ROBOT.jointLimitsDeg.pitch}°`],
              ['Joint limit — knee', `±${ROBOT.jointLimitsDeg.knee}°`],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-2">
                <dt className="text-zinc-500">{k}</dt>
                <dd className="text-zinc-200">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-3 overflow-hidden rounded-md border border-base-600/50">
            <img src="./media/walk_gait.gif" alt="Validated crawl gait, MuJoCo physics simulation" className="w-full" />
            <div className="bg-base-800/60 px-2 py-1 font-mono text-[10px] text-zinc-500">
              Crawl gait — physics + contacts, MuJoCo (not kinematic playback)
            </div>
          </div>
        </Panel>

        <Panel title="Servos" right={<SourceBadge status="real" />}>
          <div className="flex flex-col gap-3">
            {ROBOT.servos.map((sv) => (
              <div key={sv.joint} className="rounded-md border border-base-600/50 bg-base-800/40 p-3 font-mono text-xs">
                <div className="mb-1.5 uppercase tracking-wide text-amber-400">{sv.joint}</div>
                <div className="flex justify-between text-zinc-400">
                  <span>{sv.model}</span>
                  <span>{sv.voltage}</span>
                </div>
                <div className="mt-1 flex justify-between text-zinc-500">
                  <span>
                    {sv.stallKgCm} kg·cm ({sv.stallNm} N·m)
                  </span>
                  <span>{sv.speed}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 overflow-hidden rounded-md border border-base-600/50">
            <img src="./media/climb_144mm.png" alt="Validated 144 mm wall-climb pose" className="w-full" />
            <div className="bg-base-800/60 px-2 py-1 font-mono text-[10px] text-zinc-500">
              Validated 144 mm wall-climb pose
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Servo load validation" className="mt-6" right={<SourceBadge status="real" />}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] font-mono text-xs">
            <thead>
              <tr className="border-b border-base-600/60 text-left text-zinc-500">
                <th className="py-2">Joint</th>
                <th className="py-2">Worst load</th>
                <th className="py-2">RMS load</th>
                <th className="py-2">Saturated cases</th>
              </tr>
            </thead>
            <tbody>
              {ROBOT.loadValidation.map((row) => (
                <tr key={row.joint} className="border-b border-base-700/40">
                  <td className="py-2 uppercase text-zinc-300">{row.joint}</td>
                  <td className="py-2 text-zinc-400">{row.worstPct}</td>
                  <td className="py-2 text-zinc-400">{row.rmsPct}</td>
                  <td className="py-2 text-ok">{row.saturated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {ROBOT.validatedCases.map((c) => (
            <span key={c} className="label-real">
              {c}
            </span>
          ))}
        </div>
      </Panel>
    </Section>
  )
}
