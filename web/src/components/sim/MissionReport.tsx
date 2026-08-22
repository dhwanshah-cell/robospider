import type { MissionReport as ReportT } from '../../lib/sim/types'
import { StatTile } from '../ui/StatTile'
import { fmtMissionMin } from '../../lib/format'

export function MissionReport({ report }: { report: ReportT }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="kicker">Mission complete</span>
        <span className={report.returnCompleted ? 'label-real' : 'label-planned'}>
          Return {report.returnCompleted ? 'COMPLETED' : 'INCOMPLETE'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Distance travelled" value={report.distanceTravelledM.toFixed(1)} unit="m" small />
        <StatTile label="Mission time" value={fmtMissionMin(report.missionTimeS)} unit="min" small />
        <StatTile label="Max speed" value={report.maxSpeedCmS.toFixed(1)} unit="cm/s" small />
        <StatTile label="Map coverage" value={report.mapCoveragePct} unit="%" small tone="cyan" />
        <StatTile label="Observed regions" value={report.observedRegions} small />
        <StatTile
          label="Hazards identified"
          value={report.hazardsIdentified}
          small
          tone={report.hazardsIdentified > 0 ? 'risk' : 'ok'}
        />
        <StatTile label="Comm interruptions" value={report.commInterruptions} small />
        <StatTile label="Data buffered" value={report.dataBufferedMB.toFixed(2)} unit="MB" small />
      </div>
      <div className="border-t border-base-600/60 pt-3">
        <StatTile label="Final battery" value={report.finalBatteryPct.toFixed(1)} unit="%" />
      </div>
    </div>
  )
}
