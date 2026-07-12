import { COMPOUND_STYLE, type Compound } from '../../lib/tyres'

type Size = 'sm' | 'md' | 'lg'

const DIM: Record<Size, string> = {
  sm: 'h-5 w-5 text-[10px]',
  md: 'h-7 w-7 text-xs',
  lg: 'h-11 w-11 text-base',
}

interface TyreChipProps {
  compound: Compound
  size?: Size
}

export function TyreChip({ compound, size = 'md' }: TyreChipProps) {
  const s = COMPOUND_STYLE[compound]
  const text = s.darkText ? 'text-ink-dark' : 'text-ink'
  const ring = s.outline ? 'ring-1 ring-hairline' : ''
  return (
    <span
      title={compound}
      className={`inline-flex items-center justify-center rounded-full font-mono font-medium shadow-card ${s.bg} ${DIM[size]} ${text} ${ring}`}
    >
      {s.letter}
    </span>
  )
}

export function TyreSequence({
  compounds,
  size = 'md',
  arrows = false,
}: {
  compounds: Compound[]
  size?: Size
  arrows?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {compounds.map((c, i) => (
        <span key={i} className="inline-flex items-center gap-1.5">
          {arrows && i > 0 && <span className="font-body text-muted">→</span>}
          <TyreChip compound={c} size={size} />
        </span>
      ))}
    </span>
  )
}
