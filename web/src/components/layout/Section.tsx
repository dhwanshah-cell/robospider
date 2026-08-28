import type { ReactNode } from 'react'

export function Section({
  id,
  index,
  title,
  kicker,
  children,
  intro,
}: {
  id: string
  index: string
  title: string
  kicker?: string
  intro?: ReactNode
  children: ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-base-700/50 py-14 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8 flex flex-col gap-2">
          <span className="kicker">
            {index} — {kicker ?? title}
          </span>
          <h2 className="text-2xl font-bold tracking-tight text-zinc-50 sm:text-3xl">{title}</h2>
          {intro ? <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">{intro}</p> : null}
        </div>
        {children}
      </div>
    </section>
  )
}
