export function fmt1(n: number): string {
  return (Math.round(n * 10) / 10).toFixed(1)
}

export function fmt2(n: number): string {
  return (Math.round(n * 100) / 100).toFixed(2)
}

export function fmtInt(n: number): string {
  return Math.round(n).toString()
}

export function fmtClock(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function fmtMissionMin(seconds: number): string {
  return fmt1(seconds / 60)
}
