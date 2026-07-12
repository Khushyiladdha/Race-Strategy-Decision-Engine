import type { ReactNode } from 'react'

import { Button } from '../components/ui/Button'
import { ConfidenceRibbonPreview } from '../components/ui/ConfidenceRibbonPreview'
import { Delta } from '../components/ui/Delta'
import { Panel } from '../components/ui/Panel'
import { Ticker } from '../components/ui/Ticker'
import { TyreChip, TyreSequence } from '../components/ui/TyreChip'
import { formatLapTime, formatPct, formatSeconds } from '../lib/format'
import {
  SEMANTIC_TOKENS,
  SURFACE_TOKENS,
  TEXT_TOKENS,
  TYRE_TOKENS,
  type TokenSwatch,
} from '../lib/tokens-catalog'
import { ALL_COMPOUNDS } from '../lib/tyres'

function Section({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: ReactNode
}) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
        {subtitle && <p className="font-body text-sm text-muted">{subtitle}</p>}
      </div>
      {children}
    </section>
  )
}

function Label({ children }: { children: ReactNode }) {
  return (
    <span className="font-body text-[11px] uppercase tracking-wider text-muted">{children}</span>
  )
}

function Swatch({ t }: { t: TokenSwatch }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`h-10 w-10 shrink-0 rounded-chip border border-hairline ${t.bg}`} />
      <div className="min-w-0">
        <div className="font-mono text-xs text-ink">{t.name}</div>
        <div className="font-mono text-[11px] text-muted">{t.hex}</div>
        <div className="font-body text-[11px] text-muted">{t.note}</div>
      </div>
    </div>
  )
}

function SwatchGroup({ heading, tokens }: { heading: string; tokens: TokenSwatch[] }) {
  return (
    <div className="space-y-3">
      <Label>{heading}</Label>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tokens.map((t) => (
          <Swatch key={t.name} t={t} />
        ))}
      </div>
    </div>
  )
}

export function StyleGuide() {
  return (
    <div className="mx-auto max-w-5xl space-y-12 px-6 py-10">
      {/* header */}
      <header className="space-y-2">
        <h1 className="font-display text-3xl font-bold text-ink">Race Strategy — Design System</h1>
        <p className="max-w-2xl font-body text-sm text-muted">
          A pit-wall timing monitor. Tyre colors encode compound only; the purple accent is reserved
          for the single fastest / top-ranked result in view; every number is monospace. This page
          is the component gallery — Storybook is intentionally deferred.
        </p>
      </header>

      {/* colors */}
      <Section
        title="Color"
        subtitle="All tokens resolve from tokens.css — components never hard-code a hex."
      >
        <div className="space-y-8">
          <SwatchGroup heading="Surfaces" tokens={SURFACE_TOKENS} />
          <SwatchGroup heading="Text" tokens={TEXT_TOKENS} />
          <SwatchGroup heading="Semantic" tokens={SEMANTIC_TOKENS} />
          <SwatchGroup heading="Tyre compounds (chips only)" tokens={TYRE_TOKENS} />
        </div>
      </Section>

      {/* typography */}
      <Section
        title="Typography"
        subtitle="Space Grotesk (display), Inter (body), JetBrains Mono (all numbers)."
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <Label>Display · Space Grotesk</Label>
            <p className="font-display text-3xl font-bold text-ink">Leading Strategy</p>
            <p className="font-display text-xl font-medium text-ink">Section heading</p>
          </div>
          <div className="space-y-1">
            <Label>Body · Inter</Label>
            <p className="font-body text-base text-ink">
              Predicted finish assuming free-air pace and the fitted degradation model.
            </p>
            <p className="font-body text-sm text-muted">Secondary caption text.</p>
          </div>
          <div className="space-y-1">
            <Label>Data · JetBrains Mono</Label>
            <p className="font-mono text-lg text-ink tabular-nums">
              {formatLapTime(94.512)} · {formatSeconds(5651.24, 2)} · {formatPct(0.94)}
            </p>
          </div>
        </div>
      </Section>

      {/* components */}
      <Section title="Components" subtitle="Every base component in each of its states.">
        <div className="space-y-8">
          {/* Panel */}
          <div className="space-y-3">
            <Label>Panel — normal / highlighted (fastest)</Label>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Panel title="Normal panel">
                <p className="font-body text-sm text-muted">
                  The surface primitive every card builds on.
                </p>
              </Panel>
              <Panel title="Highlighted panel" highlighted>
                <p className="font-body text-sm text-muted">
                  Purple border marks the top-ranked strategy — the only legitimate accent use.
                </p>
              </Panel>
            </div>
          </div>

          {/* Button */}
          <div className="space-y-3">
            <Label>Button — variants, sizes & states</Label>
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary">Primary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="primary" disabled>
                Disabled
              </Button>
              <Button variant="primary" size="sm">
                Small
              </Button>
              <Button variant="ghost" size="sm">
                Small ghost
              </Button>
            </div>
            <p className="font-body text-[11px] text-muted">
              Focus ring and hover are interactive (tab to a button to see the cyan focus ring).
              Primary is a neutral raised fill — never the purple accent.
            </p>
          </div>

          {/* TyreChip */}
          <div className="space-y-3">
            <Label>TyreChip — every compound, plus a sequence</Label>
            <div className="flex items-center gap-2">
              {ALL_COMPOUNDS.map((c) => (
                <TyreChip key={c} compound={c} />
              ))}
            </div>
            <div className="flex items-center gap-4">
              <span className="font-body text-sm text-muted">Sequence:</span>
              <TyreSequence compounds={['SOFT', 'MEDIUM', 'HARD']} />
              <TyreSequence compounds={['SOFT', 'HARD', 'HARD']} size="sm" />
            </div>
          </div>

          {/* Delta */}
          <div className="space-y-3">
            <Label>Delta — gain / loss / zero</Label>
            <div className="flex items-center gap-6">
              <div className="flex flex-col items-start gap-1">
                <Delta seconds={-0.85} />
                <span className="font-body text-[11px] text-muted">faster (gain)</span>
              </div>
              <div className="flex flex-col items-start gap-1">
                <Delta seconds={2.3} />
                <span className="font-body text-[11px] text-muted">slower (loss)</span>
              </div>
              <div className="flex flex-col items-start gap-1">
                <Delta seconds={0} />
                <span className="font-body text-[11px] text-muted">no change</span>
              </div>
            </div>
          </div>

          {/* Ticker */}
          <div className="space-y-3">
            <Label>Ticker — short & long values</Label>
            <Ticker
              items={[
                { label: 'Leading strategy', value: 'M→H · Lap 18', fastest: true },
                { label: 'Predicted finish', value: formatLapTime(5651.24 / 60) },
                { label: 'Confidence', value: formatPct(0.94) },
              ]}
            />
            <Ticker
              items={[
                {
                  label: 'Recommendation',
                  value: 'Soft → Medium → Hard, stops on lap 14 and 36 (free-air optimum)',
                  fastest: true,
                },
                { label: 'Δ vs actual', value: '+2.30s' },
              ]}
            />
          </div>

          {/* Confidence Ribbon */}
          <div className="space-y-3">
            <Label>Confidence Ribbon (static preview) — fastest vs neutral</Label>
            <div className="space-y-2 rounded-panel border border-hairline bg-panel p-4">
              {[
                { key: 'S-M-H@14,36', mean: 5651, fastest: true },
                { key: 'S-H-S@20,41', mean: 5654, fastest: false },
                { key: 'M-H@22', mean: 5658, fastest: false },
              ].map((r) => (
                <div key={r.key} className="flex items-center gap-4">
                  <span className="w-28 font-mono text-xs text-muted">{r.key}</span>
                  <div className="flex-1">
                    <ConfidenceRibbonPreview
                      min={r.mean - 45}
                      p10={r.mean - 20}
                      mean={r.mean}
                      p90={r.mean + 28}
                      max={r.mean + 60}
                      domainLo={5590}
                      domainHi={5730}
                      fastest={r.fastest}
                    />
                  </div>
                  <span className="w-20 text-right font-mono text-xs text-ink tabular-nums">
                    {formatSeconds(r.mean, 0)}
                  </span>
                </div>
              ))}
            </div>
            <p className="font-body text-[11px] text-muted">
              Static SVG mock. The data-driven D3 version arrives in Stage 7.
            </p>
          </div>
        </div>
      </Section>

      {/* layout preview */}
      <Section title="Layout" subtitle="The three-zone pit-wall shell assembled in Stage 7.">
        <div className="grid h-44 grid-cols-[160px_1fr_180px] gap-3">
          <Panel title="Config">
            <p className="font-body text-[11px] text-muted">track · weather · fuel · SC prob</p>
          </Panel>
          <Panel title="Strategy Board" highlighted>
            <p className="font-body text-[11px] text-muted">
              ranked strategies · chips · confidence ribbons
            </p>
          </Panel>
          <Panel title="Validation">
            <p className="font-body text-[11px] text-muted">predicted vs actual</p>
          </Panel>
        </div>
      </Section>
    </div>
  )
}
