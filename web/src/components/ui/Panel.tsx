import type { ReactNode } from 'react'

export function Panel({
  title,
  right,
  children,
  className = '',
}: {
  title?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`panel flex flex-col ${className}`}>
      {title ? (
        <div className="panel-header">
          <div className="font-mono text-xs font-semibold uppercase tracking-wider text-zinc-400">{title}</div>
          {right}
        </div>
      ) : null}
      <div className="flex-1 p-4">{children}</div>
    </div>
  )
}
