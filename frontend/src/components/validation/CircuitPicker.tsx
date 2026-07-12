import type { RaceListItem } from '../../lib/api'

interface CircuitPickerProps {
  races: RaceListItem[]
  selected: string
  onSelect: (circuit: string) => void
}

// A row of chips for the small set of generatable circuits.
export function CircuitPicker({ races, selected, onSelect }: CircuitPickerProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {races
        .filter((r) => r.can_generate)
        .map((r) => (
          <button
            key={r.circuit_key}
            onClick={() => onSelect(r.circuit_key)}
            className={`rounded-chip border px-3 py-1.5 font-body text-sm transition-colors ${
              r.circuit_key === selected
                ? 'border-hairline bg-surface-raised text-ink'
                : 'border-hairline text-muted hover:text-ink'
            }`}
          >
            {r.circuit_key}
          </button>
        ))}
    </div>
  )
}
