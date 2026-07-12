// FIA tyre-compound styling in one place, so the "colors encode compound only" rule
// (build-plan §4) has a single home. TyreChip and the Stage 7 timeline/board read this.
// Class strings are full literals so Tailwind's scanner picks them up.

export type Compound = 'SOFT' | 'MEDIUM' | 'HARD' | 'INTERMEDIATE' | 'WET'

export interface CompoundStyle {
  bg: string // background utility (chips)
  fill: string // SVG fill utility (timeline bars)
  stroke: string // SVG stroke utility (line charts)
  letter: string // chip glyph
  darkText: boolean // dark ink on light compounds (medium/hard)
  outline: boolean // hard tyre needs an outline so it doesn't vanish on dark
}

export const COMPOUND_STYLE: Record<Compound, CompoundStyle> = {
  SOFT: {
    bg: 'bg-tyre-soft',
    fill: 'fill-tyre-soft',
    stroke: 'stroke-tyre-soft',
    letter: 'S',
    darkText: false,
    outline: false,
  },
  MEDIUM: {
    bg: 'bg-tyre-medium',
    fill: 'fill-tyre-medium',
    stroke: 'stroke-tyre-medium',
    letter: 'M',
    darkText: true,
    outline: false,
  },
  HARD: {
    bg: 'bg-tyre-hard',
    fill: 'fill-tyre-hard',
    stroke: 'stroke-tyre-hard',
    letter: 'H',
    darkText: true,
    outline: true,
  },
  INTERMEDIATE: {
    bg: 'bg-tyre-inter',
    fill: 'fill-tyre-inter',
    stroke: 'stroke-tyre-inter',
    letter: 'I',
    darkText: false,
    outline: false,
  },
  WET: {
    bg: 'bg-tyre-wet',
    fill: 'fill-tyre-wet',
    stroke: 'stroke-tyre-wet',
    letter: 'W',
    darkText: false,
    outline: false,
  },
}

export const DRY_COMPOUNDS: Compound[] = ['SOFT', 'MEDIUM', 'HARD']
export const ALL_COMPOUNDS: Compound[] = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
