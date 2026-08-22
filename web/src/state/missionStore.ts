import { create } from 'zustand'
import {
  blockCurrentRoute as engBlockRoute,
  forceReturn as engForceReturn,
  initialSimState,
  pauseMission as engPause,
  resumeMission as engResume,
  runPreCheck as engPreCheck,
  setGaitFrequency as engSetFreq,
  startMission as engStart,
  tick as engTick,
  triggerBatteryWarning as engBatteryWarning,
  triggerLowBattery as engLowBattery,
} from '../lib/sim/engine'
import type { CommState, SimState } from '../lib/sim/types'

const TICK_MS = 250
const DT_S = TICK_MS / 1000

interface MissionStore {
  sim: SimState
  commOverride: CommState | null
  _intervalId: ReturnType<typeof setInterval> | null
  runPreCheck: () => void
  start: () => void
  pause: () => void
  resume: () => void
  reset: () => void
  setFrequencyHz: (hz: number) => void
  simulateDegradation: () => void
  forceLinkLoss: () => void
  restoreLink: () => void
  triggerBatteryWarning: () => void
  triggerLowBattery: () => void
  blockCurrentRoute: () => void
  triggerReturn: () => void
  _ensureLoop: () => void
}

export const useMissionStore = create<MissionStore>((set, get) => ({
  sim: initialSimState(),
  commOverride: null,
  _intervalId: null,

  _ensureLoop: () => {
    if (get()._intervalId) return
    const id = setInterval(() => {
      const { sim, commOverride } = get()
      const next = engTick(sim, DT_S, { commOverride })
      set({ sim: next })
    }, TICK_MS)
    set({ _intervalId: id })
  },

  runPreCheck: () => {
    set((st) => ({ sim: engPreCheck(st.sim) }))
    get()._ensureLoop()
  },

  start: () => {
    set((st) => ({ sim: engStart(st.sim) }))
    get()._ensureLoop()
  },

  pause: () => set((st) => ({ sim: engPause(st.sim) })),
  resume: () => set((st) => ({ sim: engResume(st.sim) })),

  reset: () => {
    const id = get()._intervalId
    if (id) clearInterval(id)
    set({ sim: initialSimState(), commOverride: null, _intervalId: null })
  },

  setFrequencyHz: (hz: number) => set((st) => ({ sim: engSetFreq(st.sim, hz) })),

  simulateDegradation: () => set({ commOverride: 'DEGRADED' }),
  forceLinkLoss: () => set({ commOverride: 'LOST' }),
  restoreLink: () => set({ commOverride: null }),

  triggerBatteryWarning: () => set((st) => ({ sim: engBatteryWarning(st.sim) })),
  triggerLowBattery: () => set((st) => ({ sim: engLowBattery(st.sim) })),
  blockCurrentRoute: () => set((st) => ({ sim: engBlockRoute(st.sim) })),
  triggerReturn: () => set((st) => ({ sim: engForceReturn(st.sim) })),
}))

export function useSim() {
  return useMissionStore((s) => s.sim)
}
