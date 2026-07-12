import type { ReactNode } from 'react'

export interface TickerItem {
  label: string
  value: ReactNode
  /** Render this readout in the fastest accent (e.g. the leading strategy). */
  fastest?: boolean
}

// The persistent top-strip primitive, styled like a timing-tower ticker. Cells share a
// hairline gap; long values truncate rather than break the row.
export function Ticker({ items }: { items: TickerItem[] }) {
  return (
    <div className="flex items-stretch gap-px overflow-hidden rounded-panel border border-hairline bg-hairline">
      {items.map((it, i) => (
        <div key={i} className="flex min-w-0 flex-1 flex-col gap-0.5 bg-panel px-4 py-2">
          <span className="truncate font-body text-[10px] uppercase tracking-wider text-muted">
            {it.label}
          </span>
          <span
            className={`truncate font-mono text-sm ${it.fastest ? 'text-fastest' : 'text-ink'}`}
          >
            {it.value}
          </span>
        </div>
      ))}
    </div>
  )
}
