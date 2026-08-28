import { useState } from 'react'

const STATES = [
  { key: 'A', label: 'INTACT', desc: 'Pre-collapse structure' },
  { key: 'B', label: 'PROGRESSIVE COLLAPSE', desc: 'Structural failure in progress' },
  { key: 'C', label: 'COLLAPSED', desc: 'Rubble, voids, blocked passages' },
  { key: 'D', label: 'ROBOT DEPLOYED', desc: 'RoboSpider at the safe-zone entrance' },
] as const

function Floors({ collapse }: { collapse: number }) {
  const floors = 4
  return (
    <g>
      {Array.from({ length: floors }).map((_, i) => {
        const y = 210 - i * 42
        const tilt = collapse * (i + 1) * 2.2 * (i % 2 === 0 ? 1 : -0.6)
        const drop = collapse * i * 9
        const gap = collapse > 0.5 ? (i * 5 * collapse) : 0
        return (
          <g key={i} transform={`translate(0 ${drop + gap}) rotate(${tilt} 200 ${y})`}>
            <rect x={90 + i * 4} y={y} width={220 - i * 8} height={30} rx={2} fill="#1f232c" stroke="#3a4150" />
            {Array.from({ length: 5 }).map((_, w) => (
              <rect
                key={w}
                x={104 + i * 4 + w * 42}
                y={y + 7}
                width={16}
                height={16}
                fill={collapse > 0.6 ? '#e0503a' : '#2ea8c4'}
                opacity={0.5}
              />
            ))}
          </g>
        )
      })}
      {collapse > 0.35
        ? Array.from({ length: 10 }).map((_, i) => {
            const x = 80 + ((i * 37) % 260)
            const y = 195 + ((i * 53) % 60) * collapse
            const r = 4 + (i % 4) * 2
            return <circle key={i} cx={x} cy={y} r={r} fill="#3a4150" stroke="#161920" />
          })
        : null}
    </g>
  )
}

export function CollapseVisual() {
  const [state, setState] = useState(0)
  const collapseAmount = [0, 0.45, 1, 1][state]

  return (
    <div className="flex flex-col gap-4">
      <div className="relative aspect-[16/9] w-full overflow-hidden rounded-md border border-base-600/60 bg-[#0a0b0d]">
        <svg viewBox="0 0 400 260" className="h-full w-full">
          <rect x={0} y={230} width={400} height={30} fill="#111318" />
          <Floors collapse={collapseAmount} />
          {state === 3 ? (
            <g transform="translate(38 224)">
              <circle r={7} fill="#0c0e11" stroke="#f5a623" strokeWidth={2} />
              <path d="M 5 0 L -3 -3 L -3 3 Z" fill="#f5a623" />
              <circle r={7} fill="none" stroke="#f5a623" strokeWidth={1}>
                <animate attributeName="r" values="7;14;7" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite" />
              </circle>
            </g>
          ) : null}
        </svg>
        <div className="absolute left-3 top-3 label-tag border-cyan-400/40 bg-cyan-400/10 text-cyan-300">
          Simulated
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {STATES.map((s, i) => (
          <button
            key={s.key}
            onClick={() => setState(i)}
            className={`btn flex-col !items-start gap-0.5 !py-2 text-left ${state === i ? 'btn-primary' : ''}`}
          >
            <span className="text-[10px]">STATE {s.key}</span>
            <span className="text-[9px] font-normal normal-case text-zinc-500">{s.label}</span>
          </button>
        ))}
      </div>
      <p className="font-mono text-[11px] text-zinc-500">{STATES[state].desc}</p>
    </div>
  )
}
