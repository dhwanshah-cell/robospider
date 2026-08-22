import { useMemo } from 'react'
import { ZONE_MAP, ZONES } from '../../lib/sim/environment'
import type { SimState, Vec2, ZoneRisk } from '../../lib/sim/types'

const SCALE = 58
const ORIGIN = { x: 62, y: 172 }
const VIEW_W = 760
const VIEW_H = 340

function px(p: Vec2) {
  return { x: ORIGIN.x + p.x * SCALE, y: ORIGIN.y - p.y * SCALE }
}

const RISK_FILL: Record<ZoneRisk, string> = {
  unknown: '#3a4150',
  green: '#3ecf6e',
  yellow: '#e8c547',
  red: '#e0503a',
}
const RISK_STROKE: Record<ZoneRisk, string> = {
  unknown: '#5a6070',
  green: '#5fe08c',
  yellow: '#f0d670',
  red: '#f0776a',
}

export function SceneMap({ sim, height = 340 }: { sim: SimState; height?: number }) {
  const robotPx = px(sim.pos)

  const routeSegments = useMemo(() => {
    const segs: { a: Vec2; b: Vec2; blocked: boolean }[] = []
    for (let i = 0; i < sim.routeIds.length - 1; i++) {
      const a = ZONE_MAP[sim.routeIds[i]].pos
      const b = ZONE_MAP[sim.routeIds[i + 1]].pos
      segs.push({ a, b, blocked: false })
    }
    return segs
  }, [sim.routeIds])

  const traveledTrail = useMemo(() => {
    const pts = sim.checkpoints.map((c) => c.pos)
    return [...pts, sim.pos]
  }, [sim.checkpoints, sim.pos])

  const returnTrail = useMemo(() => {
    if (sim.missionState !== 'RETURNING' && sim.missionState !== 'SAFE_ZONE') return null
    const pts = sim.checkpoints.slice(0, sim.returnCheckpointCursor + 1).map((c) => c.pos)
    return [sim.pos, ...pts.slice().reverse()].reverse()
  }, [sim.missionState, sim.checkpoints, sim.returnCheckpointCursor, sim.pos])

  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      width="100%"
      height={height}
      className="rounded-md bg-[#0a0b0d]"
      role="img"
      aria-label="Top-down map of the collapsed structure and robot position"
    >
      <defs>
        <pattern id="rubbleHatch" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="6" stroke="#000" strokeOpacity="0.25" strokeWidth="2" />
        </pattern>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="#f5a623" />
        </marker>
      </defs>

      <rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill="url(#grid)" />
      <pattern id="grid" width="29" height="29" patternUnits="userSpaceOnUse">
        <path d="M 29 0 L 0 0 0 29" fill="none" stroke="#161920" strokeWidth="1" />
      </pattern>

      {/* corridors */}
      {routeSegments.map((seg, i) => {
        const a = px(seg.a)
        const b = px(seg.b)
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="#2a2f3a"
            strokeWidth={10}
            strokeLinecap="round"
          />
        )
      })}

      {/* all defined edges, faint, so alternate paths read as part of the structure */}
      {ZONES.map((z) =>
        z.id === 'BASE' ? null : (
          <line
            key={`faint-${z.id}`}
            x1={px(z.pos).x}
            y1={px(z.pos).y}
            x2={px(ZONE_MAP.BASE.pos).x}
            y2={px(ZONE_MAP.BASE.pos).y}
            stroke="transparent"
          />
        ),
      )}

      {/* traveled trail */}
      <polyline
        points={traveledTrail.map((p) => `${px(p).x},${px(p).y}`).join(' ')}
        fill="none"
        stroke="#2ea8c4"
        strokeWidth={3}
        strokeDasharray="1 0"
        opacity={0.85}
      />

      {/* return trail highlight */}
      {returnTrail ? (
        <polyline
          points={returnTrail.map((p) => `${px(p).x},${px(p).y}`).join(' ')}
          fill="none"
          stroke="#f5a623"
          strokeWidth={3}
          strokeDasharray="6 4"
        />
      ) : null}

      {/* zones */}
      {ZONES.map((z) => {
        const p = px(z.pos)
        const visited = sim.visitedZoneIds.has(z.id)
        const risk: ZoneRisk = visited || z.isBase ? z.groundTruth.risk : 'unknown'
        const w = z.isBase ? 64 : 82
        const h = z.isBase ? 64 : 52
        const isCurrent =
          sim.pos.x === z.pos.x && sim.pos.y === z.pos.y && (sim.missionState === 'INSPECTING' || z.isBase)
        return (
          <g key={z.id}>
            <rect
              x={p.x - w / 2}
              y={p.y - h / 2}
              width={w}
              height={h}
              rx={8}
              fill={RISK_FILL[risk]}
              fillOpacity={visited || z.isBase ? 0.28 : 0.14}
              stroke={isCurrent ? '#f5a623' : RISK_STROKE[risk]}
              strokeWidth={isCurrent ? 2.5 : 1.5}
            />
            {z.rubble ? (
              <rect x={p.x - w / 2} y={p.y - h / 2} width={w} height={h} rx={8} fill="url(#rubbleHatch)" />
            ) : null}
            <text
              x={p.x}
              y={p.y + h / 2 + 13}
              textAnchor="middle"
              className="font-mono"
              fontSize={9}
              fill="#8b93a3"
            >
              {z.id === 'BASE' ? 'BASE' : z.id}
            </text>
          </g>
        )
      })}

      {/* robot */}
      <g transform={`translate(${robotPx.x} ${robotPx.y}) rotate(${-sim.headingDeg})`}>
        <circle r={11} fill="#0c0e11" stroke="#f5a623" strokeWidth={2} />
        <path d="M 8 0 L -4 -5 L -4 5 Z" fill="#f5a623" />
      </g>
      {sim.running || sim.missionState === 'MISSION_COMPLETE' ? (
        <circle cx={robotPx.x} cy={robotPx.y} r={11} fill="none" stroke="#f5a623" strokeWidth={1}>
          <animate attributeName="r" values="11;20;11" dur="2.2s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.7;0;0.7" dur="2.2s" repeatCount="indefinite" />
        </circle>
      ) : null}
    </svg>
  )
}
