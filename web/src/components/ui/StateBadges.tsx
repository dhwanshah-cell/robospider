import type { CommState, MissionState } from '../../lib/sim/types'

const MISSION_TONE: Record<MissionState, string> = {
  IDLE: 'border-zinc-600 bg-zinc-800 text-zinc-300',
  PRE_CHECK: 'border-cyan-400/50 bg-cyan-400/10 text-cyan-300',
  DEPLOYING: 'border-cyan-400/50 bg-cyan-400/10 text-cyan-300',
  EXPLORING: 'border-ok/50 bg-ok/10 text-ok',
  INSPECTING: 'border-ok/50 bg-ok/10 text-ok',
  LINK_DEGRADED: 'border-caution/50 bg-caution/10 text-caution',
  RETURNING: 'border-amber-400/50 bg-amber-400/10 text-amber-400',
  SAFE_ZONE: 'border-ok/50 bg-ok/10 text-ok',
  LINK_LOST: 'border-risk/50 bg-risk/10 text-risk',
  SAFE_HOLD: 'border-risk/50 bg-risk/10 text-risk',
  MISSION_COMPLETE: 'border-cyan-400/50 bg-cyan-400/10 text-cyan-300',
  PAUSED: 'border-zinc-500 bg-zinc-800 text-zinc-300',
}

export function MissionStateBadge({ state }: { state: MissionState }) {
  return (
    <span className={`label-tag border px-2 py-1 text-xs ${MISSION_TONE[state]}`}>
      {state.replace(/_/g, ' ')}
    </span>
  )
}

const COMM_TONE: Record<CommState, string> = {
  GOOD: 'border-ok/50 bg-ok/10 text-ok',
  DEGRADED: 'border-caution/50 bg-caution/10 text-caution',
  CRITICAL: 'border-risk/50 bg-risk/15 text-risk',
  LOST: 'border-risk bg-risk/25 text-risk',
}

export function CommStateBadge({ state }: { state: CommState }) {
  return <span className={`label-tag border px-2 py-1 text-xs ${COMM_TONE[state]}`}>{state}</span>
}
