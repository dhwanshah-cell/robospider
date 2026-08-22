# RoboSpider — mission-control web app

Operational mission-control site for SIH25212, built around the CubeBot
engineering model in the rest of this repository. Static React/Vite app —
no backend required.

## What this is (and isn't)

This is a **browser-side, deterministic simulation** of a RoboSpider
inspection mission: gait speed, communication degradation/loss, local data
buffering, checkpoint-based return, battery-based return, and structural
hazard observations. It is explicitly labelled `SIMULATED` throughout the
UI. It does **not** run MuJoCo in the browser and does not connect to real
robot hardware — see "Architecture" below for why, and section 09 of the
site for exactly which numbers come from the validated MuJoCo model in
`../sim/` vs. which are simulated for the demo.

## Local setup

Requires Node.js 20+.

```bash
cd web
npm install
npm run dev        # http://localhost:5173
```

## Build

```bash
npm run build       # runs `tsc -b` then `vite build`, outputs to web/dist
npm run preview      # serve the production build locally
```

`npm run build` is also the exact command CI/hosting should run — it fails
on any TypeScript error, so a green build means the app type-checks.

## Architecture

```
sim/, cad/, tools/, docs/   ← validated MuJoCo model, CAD, gait/mass tooling
                                (Python; this is the engineering source of truth)
        │
        │  values transcribed by hand into web/src/data/robotSpec.ts
        ▼
web/src/lib/sim/            ← deterministic TS mission engine (pure functions):
                                environment.ts   collapsed-structure zone graph
                                engine.ts        mission/comms/battery/checkpoint
                                                 state machine, tick(state, dt)
        │
        ▼
web/src/state/missionStore.ts   ← zustand store, ticks the engine on an interval
        │
        ▼
web/src/components/             ← React UI (sections 01–09 + simulation console)
```

No MuJoCo backend is deployed for this build. Section 28 of the product
brief allows exactly this fallback when a physics backend can't be hosted
alongside the static site: keep local (Python/MuJoCo) physics and browser
visualization clearly separate, and make the browser demo deterministic and
reproducible — which this is (same inputs and control sequence always
produce the same run).

If a MuJoCo backend is stood up later (e.g. a small FastAPI + WebSocket
service on Render/Fly.io streaming real sim state), `missionStore.ts` is the
single integration point: swap its `setInterval` tick loop for a WebSocket
message handler that applies server-pushed state instead of calling
`engine.tick` locally.

## Deployment

**Frontend (this app) — Vercel:**

1. Import the repository into Vercel.
2. Root directory: `web`
3. Build command: `npm run build`
4. Output directory: `dist`
5. No environment variables are required — the app has no backend calls.

`web/vercel.json` already declares the build/output settings and an SPA
rewrite (all routes → `index.html`), so Vercel's defaults work out of the
box for the `web/` root directory.

**Any static host works identically** (Netlify, GitHub Pages, Cloudflare
Pages, S3+CloudFront): build with `npm run build` and serve `web/dist/` as
static files, with a catch-all rewrite to `index.html` for SPA routing.

There is currently no Python/MuJoCo backend deployed alongside this site —
see "Architecture" above.

## Real vs. simulated vs. planned

Summarized on the site itself (section 09) and in
`src/data/robotSpec.ts`. In short:

- **Real** — the 12-DOF chassis, measured mass, validated servo loads and
  gait speed, wall-climb pose: all sourced from this repo's `README.md` /
  `docs/HANDOFF.md`.
- **Simulated** — the collapsed-structure environment, communication
  degradation/loss, structural hazard classification, return-energy model,
  camera feed shown in the dashboard.
- **Planned** — production relay/mesh hardware, field deployment, onboard
  IMU part selection, advanced structural condition estimation.
