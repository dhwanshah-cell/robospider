import { NavBar } from './components/layout/NavBar'
import { Footer } from './components/layout/Footer'
import { Hero } from './components/sections/Hero'
import { Section01Mission } from './components/sections/Section01Mission'
import { Section02Collapse } from './components/sections/Section02Collapse'
import { Section03Robot } from './components/sections/Section03Robot'
import { Section04LiveInspection } from './components/sections/Section04LiveInspection'
import { Section05Communication } from './components/sections/Section05Communication'
import { Section06Return } from './components/sections/Section06Return'
import { Section07Structural } from './components/sections/Section07Structural'
import { Section08Simulation } from './components/sections/Section08Simulation'
import { Section09Validation } from './components/sections/Section09Validation'

export default function App() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main>
        <Hero />
        <Section01Mission />
        <Section02Collapse />
        <Section03Robot />
        <Section04LiveInspection />
        <Section05Communication />
        <Section06Return />
        <Section07Structural />
        <Section08Simulation />
        <Section09Validation />
      </main>
      <Footer />
    </div>
  )
}
