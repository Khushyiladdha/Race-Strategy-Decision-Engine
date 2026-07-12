// Palette metadata for the StyleGuide swatches. Hex lives HERE (data for display), not in
// components/pages — keeping the "no hex in components" grep gate clean. The class strings are
// full literals so Tailwind scans them.

export interface TokenSwatch {
  name: string
  bg: string // background utility used to render the swatch
  hex: string
  note: string
}

export const SURFACE_TOKENS: TokenSwatch[] = [
  { name: 'base', bg: 'bg-base', hex: '#070A10', note: 'page background' },
  { name: 'nav', bg: 'bg-nav', hex: '#0C1017', note: 'navigation bar' },
  { name: 'panel', bg: 'bg-panel', hex: '#141922', note: 'card / panel surface' },
  { name: 'hairline', bg: 'bg-hairline', hex: '#2C3344', note: 'dividers, rules, outlines' },
  {
    name: 'surface-raised',
    bg: 'bg-surface-raised',
    hex: '#1A2030',
    note: 'hover / raised (derived)',
  },
]

export const TEXT_TOKENS: TokenSwatch[] = [
  { name: 'ink', bg: 'bg-ink', hex: '#F4F6FA', note: 'primary text' },
  { name: 'muted', bg: 'bg-muted', hex: '#9BA3B7', note: 'secondary / caption' },
]

export const SEMANTIC_TOKENS: TokenSwatch[] = [
  { name: 'fastest', bg: 'bg-fastest', hex: '#9D4EDD', note: 'session-best / top-ranked ONLY' },
  { name: 'gain', bg: 'bg-gain', hex: '#22D3EE', note: 'time gained / positive' },
  { name: 'loss', bg: 'bg-loss', hex: '#F97360', note: 'time lost / negative' },
]

export const TYRE_TOKENS: TokenSwatch[] = [
  { name: 'tyre-soft', bg: 'bg-tyre-soft', hex: '#ED1C24', note: 'soft compound' },
  { name: 'tyre-medium', bg: 'bg-tyre-medium', hex: '#FFD100', note: 'medium compound' },
  { name: 'tyre-hard', bg: 'bg-tyre-hard', hex: '#F2F2F2', note: 'hard compound' },
  { name: 'tyre-inter', bg: 'bg-tyre-inter', hex: '#00A651', note: 'intermediate' },
  { name: 'tyre-wet', bg: 'bg-tyre-wet', hex: '#0072CE', note: 'wet' },
]
