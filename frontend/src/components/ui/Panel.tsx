import type { HTMLAttributes, ReactNode } from 'react'

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  /** Top-ranked / fastest context — the one legitimate use of the purple accent + glow. */
  highlighted?: boolean
  children: ReactNode
}

// Elevation: base bg -> raised card (border + card shadow) -> highlighted (purple border + glow).
export function Panel({
  title,
  highlighted = false,
  className = '',
  children,
  ...rest
}: PanelProps) {
  const elevation = highlighted ? 'border-fastest shadow-glow' : 'border-hairline shadow-card'
  return (
    <div className={`rounded-panel border bg-panel ${elevation} ${className}`} {...rest}>
      {title && (
        <div className="border-b border-hairline px-5 py-3">
          <h3 className="font-display text-sm font-medium text-ink">{title}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  )
}
