import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  children: ReactNode
}

const BASE =
  'inline-flex items-center justify-center rounded-chip font-body font-medium ' +
  'transition-[transform,background-color,border-color,color] duration-150 ' +
  'hover:-translate-y-px active:translate-y-0 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gain/60 ' +
  'disabled:opacity-40 disabled:pointer-events-none disabled:hover:translate-y-0'

// Note: the purple accent is reserved for "fastest" — buttons never use it, not even primary.
const VARIANTS: Record<Variant, string> = {
  primary: 'bg-surface-raised text-ink border border-hairline hover:bg-hairline',
  ghost: 'bg-transparent text-muted border border-hairline hover:border-muted hover:text-ink',
  danger: 'bg-transparent text-loss border border-loss/40 hover:bg-loss/10',
}

const SIZES: Record<Size, string> = {
  sm: 'text-sm px-3 py-1.5 gap-1.5',
  md: 'text-sm px-4 py-2 gap-2',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`} {...rest}>
      {children}
    </button>
  )
}
